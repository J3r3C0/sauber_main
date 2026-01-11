import os
import sys
import time
import json
import shutil
from pathlib import Path
from decimal import Decimal

# Add root to sys.path
root = Path(__file__).parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from mesh.registry.ledger_service import LedgerService, LedgerConfig
from core.ledger_journal import verify_chain, replay

RUNTIME = Path("runtime/test_settlement")

def setup_test():
    if RUNTIME.exists():
        shutil.rmtree(RUNTIME)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    
    config = LedgerConfig(
        ledger_path=RUNTIME / "ledger.json",
        journal_path=RUNTIME / "ledger_events.jsonl",
        domain_lock_path=RUNTIME / "ledger_domain.lock",
        operator_account="system:operator",
        default_margin=0.10
    )
    return LedgerService(config), config

def test_arbitrage_flow():
    print("\n--- Testing Arbitrage Flow ---")
    service, config = setup_test()
    
    # 1. Setup balances
    service.credit("user1", 1000, reason="payout_seed")
    
    # 2. Execute charge_and_settle
    # Total 100, Margin 10% => User -100, Worker +90, Operator +10
    job_id = "job_123"
    worker_id = "worker1"
    
    print(f"Executing settlement for {job_id}...")
    success = service.charge_and_settle(
        payer_id="user1",
        worker_id=worker_id,
        total_amount=100.0,
        job_id=job_id,
        note="arbitrage_test"
    )
    
    if not success:
        print("Failure: charge_and_settle returned False")
        return False
        
    # 3. Verify Balances
    balances = service.list_accounts()
    print(f"Balances: {balances}")
    
    if balances.get("user1") != 900.0:
        print(f"Failure: User1 balance mismatch! Expected 900, got {balances.get('user1')}")
        return False
    
    if balances.get("worker1") != 90.0:
        print(f"Failure: Worker1 balance mismatch! Expected 90, got {balances.get('worker1')}")
        return False
        
    if balances.get("system:operator") != 10.0:
        print(f"Failure: Operator balance mismatch! Expected 10, got {balances.get('system:operator')}")
        return False
        
    print("Success: Balances reflect 10% margin distribution.")
    
    # 4. Verify Journal Integrity
    print("Verifying Journal...")
    ok, details = verify_chain(str(config.journal_path))
    if not ok:
        print(f"Failure: Journal integrity broken! {details}")
        return False
        
    # 5. Verify Replay
    print("Verifying Replay...")
    replayed = replay(str(config.journal_path))
    replayed_balances = replayed.get("balances", {})
    
    for acc in ["user1", "worker1", "system:operator"]:
        if replayed_balances.get(acc) != balances.get(acc):
            print(f"Failure: Replay mismatch for {acc}! Replayed: {replayed_balances.get(acc)}, Actual: {balances.get(acc)}")
            return False
            
    print("Success: Replay matches current state.")
    return True

def test_idempotency():
    print("\n--- Testing Settlement Idempotency ---")
    service, config = setup_test()
    service.credit("user1", 1000)
    
    job_id = "job_once"
    worker_id = "worker1"
    
    # Call twice
    print("Calling settlement first time...")
    service.charge_and_settle("user1", worker_id, 100.0, job_id)
    
    print("Calling settlement second time...")
    service.charge_and_settle("user1", worker_id, 100.0, job_id)
    
    balances = service.list_accounts()
    if balances.get("user1") == 900.0:
        print("Success: Idempotency enforced (Payer charged only once).")
    else:
        print(f"Failure: Double charge detected! Balance: {balances.get('user1')}")
        return False
        
    return True

def test_precision():
    print("\n--- Testing Precision (ROUND_DOWN) ---")
    service, config = setup_test()
    service.credit("user1", 1000)
    
    # 10% of 105.55555 = 10.555555...
    # provider_share = quantize(105.55555 * 0.9) = 94.9999 (approx)
    # total = 105.555
    # provider = 105.555 * 0.9 = 94.9995
    # operator = 10.5555
    
    total = 105.5555
    service.charge_and_settle("user1", "worker1", total, "precision_job")
    
    balances = service.list_accounts()
    u1 = balances.get("user1")
    w1 = balances.get("worker1")
    op = balances.get("system:operator")
    
    print(f"Split of {total}: User: {u1}, Worker: {w1}, Operator: {op}")
    
    if abs((w1 + op) - total) > 0.00001:
        print(f"Failure: Sum mismatch! {w1} + {op} != {total}")
        return False
    
    return True

if __name__ == "__main__":
    success = True
    if not test_arbitrage_flow(): success = False
    if not test_idempotency(): success = False
    if not test_precision(): success = False
    
    if success:
        print("\nPHASE 5 VERIFICATION SUCCESSFUL")
    else:
        print("\nPHASE 5 VERIFICATION FAILED")
        sys.exit(1)
