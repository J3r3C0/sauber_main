"""
Service layer for the mesh fake ledger.

This module provides a high-level business API for ledger operations,
managing state persistence and providing convenient wrapper functions.
"""

from dataclasses import dataclass
from decimal import Decimal, ROUND_DOWN
from pathlib import Path
from threading import Lock
from typing import Optional, Set

from .ledger_store import (
    LedgerState,
    TransferRecord,
    load_state,
    save_state,
    ensure_account,
    get_balance,
    can_pay,
    transfer,
    get_transfers,
    AccountNotFoundError,
    InsufficientBalanceError,
    LedgerError,
)
from core.utils.atomic_io import json_lock, atomic_write_json


@dataclass
class LedgerConfig:
    """Configuration for the ledger service."""
    ledger_path: Path = Path("ledger.json")
    journal_path: Path = Path("ledger_events.jsonl")
    index_path: Path = Path("ledger_job_index.json")
    domain_lock_path: Path = Path("ledger_domain.lock")
    default_provider_account: str = "mesh_provider"
    operator_account: str = "system:operator"
    default_margin: float = 0.10
    max_margin: float = 0.40
    margin_k1: float = 0.20 # Success rate weight
    margin_k2: float = 0.10 # Latency weight
    auto_create_accounts: bool = True
    snapshot_interval: int = 100  # Create a checkpoint every 100 events
    
    # Governance Polish
    gov_enabled: bool = True
    gov_dry_run: bool = False
    settlement_rate_limit: int = 100  # per minute
    
    # Multi-Node
    mode: str = "writer"  # "writer" or "replica"
    writer_url: Optional[str] = None
    sync_interval: int = 5  # seconds
    readonly_enforced: bool = True


class LedgerService:
    """
    High-level service for ledger operations.
    
    This service manages the ledger state, handles persistence,
    and provides thread-safe access to ledger operations.
    """
    
    def __init__(self, config: Optional[LedgerConfig] = None):
        """
        Initialize the ledger service.
        
        Args:
            config: Optional configuration (uses defaults if not provided)
        """
        self.config = config or LedgerConfig()
        from core.ledger_journal import append_event, read_events
        self._append_event = append_event # Keep reference to function
        self._read_events = read_events
        self._state: LedgerState = load_state(self.config.ledger_path)
        self._lock = Lock()
        self._settled_jobs: Set[str] = set()
        self._events_since_snapshot = 0
        
        # Load idempotency index and catch up from journal
        self._load_job_index()
        
        # Ensure default provider and operator accounts exist
        with json_lock(str(self.config.domain_lock_path)):
            with self._lock:
                self._reload()
                # Ensure operator clearing account
                ensure_account(self._state, self.config.operator_account, 0)
                
                # Ensure default provider account exists
                if self.config.default_provider_account:
                    created = ensure_account(self._state, self.config.default_provider_account, 0)
                    if created:
                        self._append_event(
                            {"type": "credit", "account": self.config.default_provider_account, "amount": "0", "reason": "initial_funding"},
                            journal_path=str(self.config.journal_path),
                            domain_lock=str(self.config.domain_lock_path),
                            lock=False
                        )
                self._save()

    def _load_job_index(self) -> None:
        """Populate the settled jobs index from disk, then catch up from journal."""
        # 1. Load from persistent index file
        if self.config.index_path.exists():
            try:
                with open(self.config.index_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        self._settled_jobs.update(data)
            except Exception:
                pass

        # 2. Catch up from journal (O(N) only for events NOT in index yet)
        # Note: In v1 we scan everything if index is empty. 
        # In v2 we could store 'last_journal_offset' in the index.
        try:
            for ev in self._read_events(str(self.config.journal_path)):
                jid = ev.raw.get("job_id")
                if jid:
                    self._settled_jobs.add(str(jid))
        except Exception:
            pass

    def _save_job_index(self) -> None:
        """Persist the job index to disk."""
        try:
            atomic_write_json(str(self.config.index_path), list(self._settled_jobs))
        except Exception:
            pass
    
    def _save(self) -> None:
        """Save current state to disk (internal, assumes lock is held)."""
        save_state(self._state, self.config.ledger_path)
    
    def _reload(self) -> None:
        """Reload state from disk (internal, assumes lock is held)."""
        self._state = load_state(self.config.ledger_path)
    
    def create_account_if_missing(
        self,
        account_id: str,
        initial_balance: int = 0
    ) -> bool:
        """
        Create an account if it doesn't exist.
        """
        with json_lock(str(self.config.domain_lock_path)):
            with self._lock:
                self._reload()
                created = ensure_account(self._state, account_id, initial_balance)
                if created:
                    self._append_event(
                        {"type": "credit", "account": account_id, "amount": str(initial_balance), "reason": "initial_funding"},
                        journal_path=str(self.config.journal_path),
                        domain_lock=str(self.config.domain_lock_path),
                        lock=False
                    )
                    self._save()
                return created
    
    def get_balance(self, account_id: str) -> int:
        """
        Get account balance.
        
        Args:
            account_id: Account identifier
            
        Returns:
            Account balance
            
        Raises:
            AccountNotFoundError: If account doesn't exist
        """
        with self._lock:
            return get_balance(self._state, account_id)
    
    def require_balance(self, payer_id: str, amount: int) -> bool:
        """
        Check if an account has sufficient balance.
        """
        with json_lock(str(self.config.domain_lock_path)):
            with self._lock:
                self._reload()
                return can_pay(self._state, payer_id, amount)
    
    def charge(
        self,
        payer_id: str,
        receiver_id: str,
        amount: int,
        job_id: Optional[str] = None,
        note: Optional[str] = None
    ) -> TransferRecord:
        """
        Charge tokens from payer to receiver.
        """
        with json_lock(str(self.config.domain_lock_path)):
            with self._lock:
                self._reload()
                # Auto-create accounts if configured
                if self.config.auto_create_accounts:
                    ensure_account(self._state, payer_id, 0)
                    ensure_account(self._state, receiver_id, 0)
                
                # Journal First
                self._append_event(
                    {
                        "type": "charge", 
                        "account": payer_id, 
                        "amount": str(amount), 
                        "job_id": job_id, 
                        "worker_id": receiver_id, 
                        "reason": note or "job_execution"
                    },
                    journal_path=str(self.config.journal_path),
                    domain_lock=str(self.config.domain_lock_path),
                    lock=False
                )
                
                record = transfer(self._state, payer_id, receiver_id, amount, job_id, note)
                self._save()
                return record
    
    def credit(
        self,
        account_id: str,
        amount: int,
        reason: Optional[str] = None
    ) -> TransferRecord:
        """
        Credit tokens to an account (admin/god mode).
        """
        system_account = "system"
        
        with json_lock(str(self.config.domain_lock_path)):
            with self._lock:
                self._reload()
                # Ensure system account exists with unlimited balance
                if system_account not in self._state["accounts"]:
                    ensure_account(self._state, system_account, 10**18)  # Effectively unlimited
                
                # Ensure target account exists
                if self.config.auto_create_accounts:
                    ensure_account(self._state, account_id, 0)
                
                # Give system account enough balance if needed
                if self._state["accounts"][system_account]["balance"] < amount:
                    self._state["accounts"][system_account]["balance"] = 10**18
                
                # Journal First
                self._append_event(
                    {"type": "credit", "account": account_id, "amount": str(amount), "reason": reason or "manual_credit"},
                    journal_path=str(self.config.journal_path),
                    domain_lock=str(self.config.domain_lock_path),
                    lock=False
                )
                
                record = transfer(self._state, system_account, account_id, amount, None, reason)
                self._save()
                return record
    
    def get_transfers(
        self,
        account_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> list[TransferRecord]:
        """
        Get transfer history.
        
        Args:
            account_id: Optional account to filter by
            limit: Optional limit on number of records
            
        Returns:
            List of transfer records, newest first
        """
        with self._lock:
            return get_transfers(self._state, account_id, limit)
    
    def account_exists(self, account_id: str) -> bool:
        """
        Check if an account exists.
        
        Args:
            account_id: Account identifier
            
        Returns:
            True if account exists, False otherwise
        """
        with self._lock:
            return account_id in self._state["accounts"]
    
    def list_accounts(self) -> dict[str, int]:
        """
        List all accounts and their balances.
        
        Returns:
            Dictionary mapping account IDs to balances
        """
        with self._lock:
            return {
                account_id: account["balance"]
                for account_id, account in self._state["accounts"].items()
            }

    def calculate_margin(self, success_ema: float, latency_ema: float) -> float:
        """
        Calculates a risk-adjusted margin based on worker performance.
        
        effective_margin = clamp(
            base_margin 
            + k1 * (1 - success_ema) 
            + k2 * clamp(latency_ema / LAT_CAP, 0, 1),
            min_margin, max_margin
        )
        """
        # lat_cap from MeshConfig is usually 1500ms
        LAT_CAP = 1500.0 
        
        k1 = self.config.margin_k1
        k2 = self.config.margin_k2
        base = self.config.default_margin
        
        rel_penalty = k1 * (1.0 - max(0.0, min(1.0, success_ema)))
        lat_factor = max(0.0, min(1.0, latency_ema / LAT_CAP))
        lat_penalty = k2 * lat_factor
        
        margin = base + rel_penalty + lat_penalty
        
        # Clamp between base (min) and max
        return max(base, min(self.config.max_margin, margin))

    def charge_and_settle(
        self,
        payer_id: str,
        worker_id: str,
        total_amount: float,
        job_id: str,
        margin: Optional[float] = None,
        note: Optional[str] = None
    ) -> bool:
        """
        Execute an atomic arbitrage settlement:
        1. Charge Payer -> Operator (Total)
        2. Transfer Operator -> Worker (Provider Share)
        
        Returns True if settlement succeeded or was already done (idempotent).
        """
        # Governance: Readonly enforcement
        if self.config.mode == "replica" and self.config.readonly_enforced:
            raise RuntimeError("Replica nodes cannot execute settlements (readonly enforced)")
        
        # Governance: Master switch
        if not self.config.gov_enabled:
            return True  # Silently skip if governance disabled
        
        if not job_id:
            raise ValueError("job_id is required for settlement")
            
        with json_lock(str(self.config.domain_lock_path)):
            with self._lock:
                self._reload()
                
                # 1. Idempotency Check
                if job_id in self._settled_jobs:
                    return True
                
                # 2. Precision Calculation
                Q = Decimal("0.0001")
                def d(x) -> Decimal: return Decimal(str(x))
                
                total = d(total_amount)
                m = d(margin if margin is not None else self.config.default_margin)
                
                provider_share = (total * (Decimal("1") - m)).quantize(Q, rounding=ROUND_DOWN)
                
                # Governance: Dry-run mode
                if self.config.gov_dry_run:
                    print(f"[DRY-RUN] Settlement for {job_id[:8]}: margin={float(m):.4f}, provider_share={float(provider_share):.4f}")
                    return True
                
                # 3. Balance Check
                if not can_pay(self._state, payer_id, float(total)):
                    return False
                    
                # 4. Atomic Execution
                operator = self.config.operator_account
                ensure_account(self._state, payer_id, 0)
                ensure_account(self._state, worker_id, 0)
                ensure_account(self._state, operator, 0)
                
                # A) Charge Payer -> Operator
                self._append_event(
                    {
                        "type": "charge",
                        "account": payer_id,
                        "to_account": operator, # Make it double-entry
                        "amount": str(total),
                        "job_id": job_id,
                        "worker_id": worker_id,
                        "reason": note or f"job_payment:{job_id}"
                    },
                    journal_path=str(self.config.journal_path),
                    domain_lock=str(self.config.domain_lock_path),
                    lock=False
                )
                transfer(self._state, payer_id, operator, float(total), job_id, note)
                
                # B) Transfer Operator -> Worker
                self._append_event(
                    {
                        "type": "transfer",
                        "account": operator,
                        "to_account": worker_id,
                        "amount": str(provider_share),
                        "job_id": job_id,
                        "worker_id": worker_id,
                        "reason": f"provider_payout:{job_id}"
                    },
                    journal_path=str(self.config.journal_path),
                    domain_lock=str(self.config.domain_lock_path),
                    lock=False
                )
                transfer(self._state, operator, worker_id, float(provider_share), job_id, note)
                
                # 5. Commit
                self._save()
                return True

    def batch_settle(
        self,
        settlements: list[dict] # list of dicts with payer_id, worker_id, total_amount, job_id, margin, note
    ) -> list[bool]:
        """
        Execute multiple arbitrage settlements in a single atomic cycle.
        Massively increases throughput by reducing lock contention and I/O.
        """
        results = []
        if not settlements:
            return []

        with json_lock(str(self.config.domain_lock_path)):
            with self._lock:
                self._reload()
                
                Q = Decimal("0.0001")
                def d(x) -> Decimal: return Decimal(str(x))
                operator = self.config.operator_account
                
                any_change = False
                
                for s in settlements:
                    job_id = s.get("job_id")
                    if not job_id:
                        results.append(False)
                        continue
                    if job_id in self._settled_jobs:
                        results.append(True)
                        continue
                    
                    payer_id = s.get("payer_id")
                    worker_id = s.get("worker_id")
                    total_amount = s.get("total_amount", 0)
                    margin = s.get("margin")
                    note = s.get("note")
                    
                    total = d(total_amount)
                    m = d(margin if margin is not None else self.config.default_margin)
                    provider_share = (total * (Decimal("1") - m)).quantize(Q, rounding=ROUND_DOWN)
                    
                    if not can_pay(self._state, payer_id, float(total)):
                        results.append(False)
                        continue
                        
                    # Prepare accounts
                    ensure_account(self._state, payer_id, 0)
                    ensure_account(self._state, worker_id, 0)
                    ensure_account(self._state, operator, 0)
                    
                    # Journal & Transfer
                    self._append_event(
                        {
                            "type": "charge", "account": payer_id, "to_account": operator,
                            "amount": str(total), "job_id": job_id, "worker_id": worker_id,
                            "reason": note or f"batch_payment:{job_id}"
                        },
                        journal_path=str(self.config.journal_path), domain_lock=str(self.config.domain_lock_path), lock=False
                    )
                    transfer(self._state, payer_id, operator, float(total), job_id, note)
                    
                    self._append_event(
                        {
                            "type": "transfer", "account": operator, "to_account": worker_id,
                            "amount": str(provider_share), "job_id": job_id, "worker_id": worker_id,
                            "reason": f"batch_payout:{job_id}"
                        },
                        journal_path=str(self.config.journal_path), domain_lock=str(self.config.domain_lock_path), lock=False
                    )
                    transfer(self._state, operator, worker_id, float(provider_share), job_id, note)
                    
                    self._settled_jobs.add(job_id)
                    results.append(True)
                    any_change = True
                    self._events_since_snapshot += 2

                if any_change:
                    self._save()
                    self._save_job_index()
                    
                    if self._events_since_snapshot >= self.config.snapshot_interval:
                        # In v1, our ledger.json IS the snapshot. reset counter.
                        self._events_since_snapshot = 0
                
                return results
