"""
Unified client interface for the mesh fake ledger.

This client can work in two modes:
1. Direct mode: Directly accesses the JSON file (for local, same-process usage)
2. HTTP mode: Uses HTTP API (for distributed, multi-service usage)

Example:
    # Local mode
    ledger = LedgerClient(json_path="ledger.json")
    
    # Remote mode
    ledger = LedgerClient(base_url="http://ledger-api:8000")
    
    # Usage (same interface regardless of mode)
    if ledger.can_pay("user1", 10):
        ledger.charge("user1", "provider", 10, job_id="job_123")
"""

from typing import Optional
from pathlib import Path
import requests


class PaymentRequiredError(Exception):
    """
    Raised when an account has insufficient balance for a payment.
    
    This exception should be caught by FastAPI services and converted
    to HTTP 402 Payment Required responses.
    """
    
    def __init__(self, required: int, balance: int, account_id: str):
        """
        Initialize the payment error.
        
        Args:
            required: Required token amount
            balance: Current account balance
            account_id: Account that lacks sufficient balance
        """
        self.required = required
        self.balance = balance
        self.account_id = account_id
        super().__init__(
            f"Payment required: account '{account_id}' has {balance} tokens, "
            f"needs {required} tokens (shortfall: {required - balance})"
        )
    
    def to_json(self) -> dict:
        """Convert to JSON-serializable dict for HTTP 402 responses."""
        return {
            "error": "payment_required",
            "required_tokens": self.required,
            "current_balance": self.balance,
            "shortfall": self.required - self.balance,
            "account_id": self.account_id
        }
    
    def to_http_detail(self) -> dict:
        """Alias for to_json, semantically for FastAPI HTTP detail."""
        return self.to_json()
    
    def to_http_exception(self):
        """Create FastAPI HTTPException from this error."""
        from fastapi import HTTPException
        return HTTPException(status_code=402, detail=self.to_json())


class LedgerClient:
    """
    Unified client interface for ledger operations.
    
    Supports both direct JSON file access and HTTP API access with
    the same interface.
    """
    
    @property
    def mode(self) -> str:
        return "direct" if self._service is not None else "http"
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        json_path: Optional[str] = None
    ):
        """
        Initialize ledger client.
        
        Args:
            base_url: HTTP API base URL (e.g., "http://localhost:8000")
            json_path: Path to JSON ledger file (for direct mode)
            
        Note:
            Exactly one of base_url or json_path must be provided.
            If json_path is provided, uses direct file access.
            If base_url is provided, uses HTTP API.
        """
        if base_url and json_path:
            raise ValueError("Specify either base_url OR json_path, not both")
        if not base_url and not json_path:
            raise ValueError("Must specify either base_url or json_path")
        
        self.base_url = base_url
        self.json_path = Path(json_path) if json_path else None
        self._service = None
        
        # In direct mode, initialize the service
        if self.json_path:
            from .ledger_service import LedgerService, LedgerConfig
            self._service = LedgerService(LedgerConfig(ledger_path=self.json_path))
    
    def get_balance(self, account_id: str) -> int:
        """
        Get the balance of an account.
        
        Args:
            account_id: Account identifier
            
        Returns:
            Current balance in tokens
            
        Raises:
            Exception: If account not found or API error
        """
        if self._service:
            # Direct mode
            return self._service.get_balance(account_id)
        else:
            # HTTP mode
            response = requests.get(
                f"{self.base_url}/accounts/{account_id}/balance",
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            return int(data["balance"])
    
    def can_pay(self, account_id: str, amount: int) -> bool:
        """
        Check if an account can pay the specified amount.
        
        Args:
            account_id: Account identifier
            amount: Required amount in tokens
            
        Returns:
            True if account has sufficient balance, False otherwise
        """
        if self._service:
            # Direct mode
            return self._service.require_balance(account_id, amount)
        else:
            # HTTP mode
            try:
                balance = self.get_balance(account_id)
                return balance >= amount
            except Exception:
                return False
    
    def charge(
        self,
        payer_id: str,
        receiver_id: str,
        amount: int,
        job_id: Optional[str] = None
    ) -> dict:
        """
        Charge tokens from payer to receiver.
        
        Args:
            payer_id: Payer account identifier
            receiver_id: Receiver account identifier
            amount: Amount to charge in tokens
            job_id: Optional job identifier for tracking
            
        Returns:
            Transfer record as dict
            
        Raises:
            PaymentRequiredError: If payer has insufficient balance
            Exception: If accounts not found or other API error
        """
        # Check balance first - this applies to both modes
        if not self.can_pay(payer_id, amount):
            balance = self.get_balance(payer_id)
            raise PaymentRequiredError(
                required=amount,
                balance=balance,
                account_id=payer_id
            )
        
        if self._service:
            # Direct mode
            from .ledger_store import InsufficientBalanceError, AccountNotFoundError
            try:
                record = self._service.charge(payer_id, receiver_id, amount, job_id)
                return dict(record)
            except InsufficientBalanceError:
                balance = self._service.get_balance(payer_id)
                raise PaymentRequiredError(
                    required=amount,
                    balance=balance,
                    account_id=payer_id
                )
        else:
            # HTTP mode
            response = requests.post(
                f"{self.base_url}/transfers",
                json={
                    "from_account": payer_id,
                    "to_account": receiver_id,
                    "amount": amount,
                    "job_id": job_id,
                },
                timeout=5,
            )
            
            if response.status_code == 400:
                try:
                    data = response.json()
                    if data.get("error") == "insufficient_balance":
                        balance = self.get_balance(payer_id)
                        raise PaymentRequiredError(
                            required=amount,
                            balance=balance,
                            account_id=payer_id,
                        )
                except Exception:
                    balance = self.get_balance(payer_id)
                    raise PaymentRequiredError(
                        required=amount,
                        balance=balance,
                        account_id=payer_id,
                    )
            
            response.raise_for_status()
            return response.json()["transfer"]
    
    def ensure_account(self, account_id: str, initial_balance: int = 0) -> bool:
        """
        Ensure an account exists, creating it if necessary.
        
        Args:
            account_id: Account identifier
            initial_balance: Initial balance for new accounts
            
        Returns:
            True if account was created, False if it already existed
        """
        if self._service:
            # Direct mode
            return self._service.create_account_if_missing(account_id, initial_balance)
        else:
            # HTTP mode
            response = requests.post(
                f"{self.base_url}/accounts/{account_id}/ensure",
                json={"initial_balance": initial_balance},
                timeout=5,
            )
            response.raise_for_status()
            data = response.json()
            return bool(data.get("created", False))
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
        Execute an atomic arbitrage settlement.
        
        Args:
            payer_id: Payer account identifier
            worker_id: Worker account identifier
            total_amount: Total amount to charge payer
            job_id: Job identifier for idempotency
            margin: Optional margin override
            note: Optional note
            
        Returns:
            True if settlement succeeded or was already settled.
        """
        if self._service:
            # Direct mode
            return self._service.charge_and_settle(
                payer_id=payer_id,
                worker_id=worker_id,
                total_amount=total_amount,
                job_id=job_id,
                margin=margin,
                note=note
            )
        else:
            # HTTP mode
            response = requests.post(
                f"{self.base_url}/settlement",
                json={
                    "payer_id": payer_id,
                    "worker_id": worker_id,
                    "total_amount": total_amount,
                    "job_id": job_id,
                    "margin": margin,
                    "note": note
                },
                timeout=10,
            )
            response.raise_for_status()
            return response.json().get("success", True)
