import time
import shutil
import sys
from pathlib import Path

# Add root to sys.path
root = Path(__file__).parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from mesh.registry.ledger_service import LedgerService, LedgerConfig

RUNTIME = Path("runtime/test_throughput")

def setup():
    if RUNTIME.exists():
        shutil.rmtree(RUNTIME)
    RUNTIME.mkdir(parents=True, exist_ok=True)
    config = LedgerConfig(
        ledger_path=RUNTIME / "ledger.json",
        journal_path=RUNTIME / "ledger_events.jsonl",
        index_path=RUNTIME / "job_index.json",
        domain_lock_path=RUNTIME / "ledger_domain.lock"
    )
    service = LedgerService(config)
    service.credit("user1", 100000)
    return service

def test_throughput():
    service = setup()
    N = 100
    
    # 1. Individual
    print(f"\n--- Testing {N} individual settlements ---")
    start = time.time()
    for i in range(N):
        service.charge_and_settle("user1", "worker1", 1.0, f"indiv_{i}")
    indiv_time = time.time() - start
    print(f"Time: {indiv_time:.2f}s ({N/indiv_time:.1f} ops/s)")
    
    # 2. Batch
    service = setup()
    print(f"\n--- Testing {N} settlements in 10 batches ---")
    batch_size = 10
    batches = []
    for b in range(N // batch_size):
        batch = []
        for i in range(batch_size):
            batch.append({
                "payer_id": "user1",
                "worker_id": "worker1",
                "total_amount": 1.0,
                "job_id": f"batch_{b}_{i}"
            })
        batches.append(batch)
    
    start = time.time()
    for batch in batches:
        service.batch_settle(batch)
    batch_time = time.time() - start
    print(f"Time: {batch_time:.2f}s ({N/batch_time:.1f} ops/s)")
    
    gain = (indiv_time / batch_time)
    print(f"\nThroughput Gain: {gain:.1f}x")
    
    if gain < 1.0:
        print("Failure: Batching did not improve throughput!")
        return False
        
    return True

if __name__ == "__main__":
    if test_throughput():
        print("\nPHASE 6 VERIFICATION SUCCESSFUL")
    else:
        sys.exit(1)
