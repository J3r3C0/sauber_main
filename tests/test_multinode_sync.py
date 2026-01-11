import sys
import time
from pathlib import Path

# Add root to sys.path
root = Path(__file__).parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from mesh.registry.ledger_service import LedgerService, LedgerConfig
from mesh.registry.replica_sync import ReplicaSyncService

def test_multinode_sync():
    print("--- Testing Multi-Node Sync ---")
    
    # Setup Writer
    writer_config = LedgerConfig(
        ledger_path=Path("runtime/writer/ledger.json"),
        journal_path=Path("runtime/writer/ledger_events.jsonl"),
        domain_lock_path=Path("runtime/writer/ledger_domain.lock"),
        mode="writer"
    )
    writer_config.ledger_path.parent.mkdir(parents=True, exist_ok=True)
    
    writer = LedgerService(writer_config)
    writer.credit("user1", 10000)
    
    # Create some settlements
    print("\n1. Creating 10 settlements on writer...")
    for i in range(10):
        writer.charge_and_settle(
            payer_id="user1",
            worker_id="worker1",
            total_amount=10.0,
            job_id=f"job_{i}"
        )
    
    writer_balance = writer.get_balance("worker1")
    print(f"   Writer worker1 balance: {writer_balance}")
    
    # Setup Replica
    replica_config = LedgerConfig(
        ledger_path=Path("runtime/replica/ledger.json"),
        journal_path=Path("runtime/replica/ledger_events.jsonl"),
        domain_lock_path=Path("runtime/replica/ledger_domain.lock"),
        mode="replica",
        writer_url="http://localhost:8100",
        readonly_enforced=True
    )
    replica_config.ledger_path.parent.mkdir(parents=True, exist_ok=True)
    
    replica = LedgerService(replica_config)
    
    # Start Writer HTTP API in background
    print("\n2. Starting Writer HTTP API...")
    import subprocess
    import os
    env = os.environ.copy()
    env["LEDGER_JOURNAL_PATH"] = str(writer_config.journal_path)
    env["LEDGER_JOURNAL_HTTP_PORT"] = "8100"
    
    writer_api = subprocess.Popen(
        [sys.executable, "-m", "mesh.registry.journal_sync_api"],
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for API to start
    time.sleep(2)
    
    # Sync replica
    print("\n3. Syncing replica...")
    sync_service = ReplicaSyncService(
        writer_url="http://localhost:8100",
        state_path=Path("runtime/replica/replica_state.json"),
        ledger_service=replica
    )
    
    success = sync_service.sync_once()
    if not success:
        print("   ERROR: Sync failed!")
        writer_api.terminate()
        return False
    
    replica_balance = replica.get_balance("worker1")
    print(f"   Replica worker1 balance: {replica_balance}")
    
    # Verify consistency
    if abs(writer_balance - replica_balance) < 0.01:
        print("\n✅ PHASE 8 VERIFICATION SUCCESSFUL")
        print(f"   Balances match: {writer_balance} == {replica_balance}")
        result = True
    else:
        print("\n❌ PHASE 8 VERIFICATION FAILED")
        print(f"   Balance mismatch: {writer_balance} != {replica_balance}")
        result = False
    
    # Cleanup
    writer_api.terminate()
    writer_api.wait()
    
    return result

if __name__ == "__main__":
    if test_multinode_sync():
        sys.exit(0)
    else:
        sys.exit(1)
