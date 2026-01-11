"""
Replica Sync Service.

Periodically syncs journal from writer node and applies events to local state.
"""
import json
import time
import requests
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, asdict

@dataclass
class ReplicaState:
    writer_url: str
    sync_offset: int = 0
    last_hash: str = ""
    last_event_ts: float = 0.0
    last_sync_at: float = 0.0
    total_events_synced: int = 0

class ReplicaSyncService:
    def __init__(self, writer_url: str, state_path: Path, ledger_service):
        self.writer_url = writer_url
        self.state_path = state_path
        self.ledger = ledger_service
        self.partial_buffer = ""
        self.state = self._load_state()
    
    def _load_state(self) -> ReplicaState:
        """Load replica state from disk."""
        if self.state_path.exists():
            try:
                with open(self.state_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return ReplicaState(**data)
            except Exception:
                pass
        return ReplicaState(writer_url=self.writer_url)
    
    def _save_state(self):
        """Save replica state to disk."""
        with open(self.state_path, 'w', encoding='utf-8') as f:
            json.dump(asdict(self.state), f, indent=2)
    
    def sync_once(self) -> bool:
        """
        Fetch and apply new events from writer.
        Returns True if sync succeeded, False if writer unreachable.
        """
        try:
            # Fetch chunk from writer
            resp = requests.get(
                f"{self.writer_url}/journal",
                params={"offset": self.state.sync_offset},
                timeout=10
            )
            resp.raise_for_status()
            
            chunk = resp.text
            next_offset = int(resp.headers.get('X-Journal-Next-Offset', self.state.sync_offset))
            last_hash = resp.headers.get('X-Journal-Last-Hash', '')
            last_ts = float(resp.headers.get('X-Journal-Last-TS', 0))
            
            # Handle partial lines
            if self.partial_buffer:
                chunk = self.partial_buffer + chunk
                self.partial_buffer = ""
            
            if chunk and not chunk.endswith('\n'):
                last_newline = chunk.rfind('\n')
                if last_newline >= 0:
                    self.partial_buffer = chunk[last_newline+1:]
                    chunk = chunk[:last_newline+1]
                else:
                    self.partial_buffer = chunk
                    chunk = ""
            
            # Apply events
            events_applied = 0
            for line in chunk.splitlines():
                if not line.strip():
                    continue
                try:
                    event = json.loads(line)
                    self._apply_event(event)
                    events_applied += 1
                except Exception as e:
                    print(f"[replica] Error applying event: {e}")
            
            # Update state
            self.state.sync_offset = next_offset
            if last_hash:
                self.state.last_hash = last_hash
            if last_ts:
                self.state.last_event_ts = last_ts
            self.state.last_sync_at = time.time()
            self.state.total_events_synced += events_applied
            self._save_state()
            
            if events_applied > 0:
                print(f"[replica] Synced {events_applied} events (offset: {next_offset})")
            
            return True
            
        except Exception as e:
            print(f"[replica] Sync failed: {e}")
            return False
    
    def _apply_event(self, event: dict):
        """Apply a single event to the ledger state."""
        # This uses the same logic as replay() but for a single event
        from mesh.registry.ledger_store import ensure_account, transfer
        
        state = self.ledger._state
        etype = event.get("type")
        account = event.get("account", "")
        to_account = event.get("to_account", "")
        amount = float(event.get("amount", 0))
        
        if to_account:
            # Double-entry
            ensure_account(state, account, 0)
            ensure_account(state, to_account, 0)
            state["accounts"][account]["balance"] -= amount
            state["accounts"][to_account]["balance"] += amount
        elif etype == "credit":
            ensure_account(state, account, 0)
            state["accounts"][account]["balance"] += amount
        elif etype in ["debit", "charge"]:
            ensure_account(state, account, 0)
            state["accounts"][account]["balance"] -= amount
        elif etype == "adjust":
            ensure_account(state, account, 0)
            state["accounts"][account]["balance"] += amount
        
        # Save state after each event (or batch for performance)
        self.ledger._save()
    
    def run_loop(self, interval: int = 5):
        """Run continuous sync loop."""
        print(f"[replica] Starting sync loop (interval: {interval}s)")
        while True:
            self.sync_once()
            time.sleep(interval)

if __name__ == "__main__":
    import sys
    import os
    from mesh.registry.ledger_service import LedgerService, LedgerConfig
    
    writer_url = os.getenv("LEDGER_WRITER_URL", "http://localhost:8100")
    sync_interval = int(os.getenv("LEDGER_SYNC_INTERVAL", "5"))
    
    config = LedgerConfig(
        mode="replica",
        writer_url=writer_url,
        readonly_enforced=True
    )
    
    ledger = LedgerService(config)
    replica = ReplicaSyncService(
        writer_url=writer_url,
        state_path=Path("replica_state.json"),
        ledger_service=ledger
    )
    
    replica.run_loop(interval=sync_interval)
