import os
import sys
import time
import json
import shutil
from pathlib import Path

# Add root to sys.path
root = Path(__file__).parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from mesh.registry.ledger_service import LedgerService, LedgerConfig
from core.ledger_journal import verify_chain, replay

RUNTIME = Path("runtime/test_journal")

def setup_test():
    if RUNTIME.exists():
        shutil.rmtree(RUNTIME)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    
    config = LedgerConfig(
        ledger_path=RUNTIME / "ledger.json",
        journal_path=RUNTIME / "ledger_events.jsonl",
        domain_lock_path=RUNTIME / "ledger_domain.lock"
    )
    return LedgerService(config), config

def test_journal_integrity():
    print("\n--- Testing Journal Integrity ---")
    service, config = setup_test()
    
    # Perform some operations
    service.credit("user1", 100, reason="test_funding")
    service.charge("user1", "worker1", 10, job_id="job123", note="test_charge")
    
    journal_path = str(config.journal_path)
    
    # 1. Verify chain
    print("Verifying hash chain...")
    ok, details = verify_chain(journal_path)
    if ok:
        print(f"Success: Hash chain is valid. ({details.get('events')} events)")
    else:
        print(f"Failure: Hash chain is invalid! {details}")
        return False
        
    # 2. Verify replay equivalence
    print("Verifying replay equivalence...")
    replayed_full_state = replay(journal_path)
    replayed_balances = replayed_full_state.get("balances", {})
    current_balances = service.list_accounts()
    
    # Note: user1 should have 90.0
    u1_replayed = replayed_balances.get("user1")
    u1_actual = current_balances.get("user1")
    
    if u1_replayed == u1_actual == 90.0:
        print(f"Success: User1 balance match (90.0)")
    else:
        print(f"Failure: Balance mismatch! Replayed: {u1_replayed}, Actual: {u1_actual}")
        return False

    return True

def test_tampering():
    print("\n--- Testing Tamper Detection ---")
    service, config = setup_test()
    service.credit("user1", 100)
    
    journal_path = config.journal_path
    
    # Tamper with the file
    lines = journal_path.read_text(encoding="utf-8").splitlines()
    if not lines: return False
    
    data = json.loads(lines[-1])
    data["amount"] = "999999" # Tamper
    lines[-1] = json.dumps(data, separators=(",", ":")) # User uses separators=(",", ":")
    journal_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    
    ok, details = verify_chain(str(journal_path))
    if not ok:
        print(f"Success: Tampering detected! ({details.get('reason')})")
        return True
    else:
        print("Failure: Tampering NOT detected!")
        return False

def test_concurrent_appends():
    print("\n--- Testing Concurrent Journal Appends ---")
    service, config = setup_test()
    
    import threading
    
    def worker_thread(tid):
        for i in range(10):
            service.credit(f"thread_{tid}", 1)
            time.sleep(0.01)
            
    threads = []
    for i in range(5):
        t = threading.Thread(target=worker_thread, args=(i,))
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    journal_path = str(config.journal_path)
    ok, details = verify_chain(journal_path)
    if ok:
        print("Success: Chain intact after concurrent appends.")
        
        replayed_full = replay(journal_path)
        replayed_balances = replayed_full.get("balances", {})
        expected_total = 50.0 # 5 threads * 10 credits
        actual_total = sum(replayed_balances.get(f"thread_{i}", 0.0) for i in range(5))
        if actual_total == expected_total:
            print(f"Success: Total amount match ({actual_total})")
            return True
        else:
            print(f"Failure: Total amount mismatch! Expected {expected_total}, got {actual_total}")
            return False
    else:
        print(f"Failure: Chain broken after concurrent appends! {details}")
        return False

if __name__ == "__main__":
    success = True
    if not test_journal_integrity(): success = False
    if not test_tampering(): success = False
    if not test_concurrent_appends(): success = False
    
    if success:
        print("\nPHASE 4 VERIFICATION SUCCESSFUL")
    else:
        print("\nPHASE 4 VERIFICATION FAILED")
        sys.exit(1)
