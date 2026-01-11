import sys
import time
from pathlib import Path

# Add root to sys.path
root = Path(__file__).parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from mesh.registry.ledger_service import LedgerService, LedgerConfig
from mesh.registry.mesh_registry import WorkerRegistry, WorkerStats, WorkerInfo, WorkerCapability

def test_governance():
    print("--- Testing Arbitrage Governance & SLA ---")
    
    # Setup
    config = LedgerConfig(default_margin=0.10)
    service = LedgerService(config)
    
    # 1. Test Margin Calculation
    print("\n1. Testing Dynamic Margin:")
    # Perfect worker (1.0 success, 0 latency)
    m_perfect = service.calculate_margin(1.0, 0.0)
    print(f"  Perfect (1.0, 0ms):    {m_perfect:.4f} (Expected: 0.1000)")
    
    # Risky worker (0.8 success, 900ms latency)
    # 0.10 + 0.2*(0.2) + 0.1*(900/1500) = 0.10 + 0.04 + 0.06 = 0.20
    m_risky = service.calculate_margin(0.8, 900.0)
    print(f"  Risky (0.8, 900ms):    {m_risky:.4f} (Expected: 0.2000)")
    
    # Failed worker (0.5 success, 2000ms latency)
    # 0.10 + 0.2*(0.5) + 0.1*(1.0) = 0.10 + 0.10 + 0.10 = 0.30
    m_failed = service.calculate_margin(0.5, 2000.0)
    print(f"  Failed (0.5, 2000ms):  {m_failed:.4f} (Expected: 0.3000)")

    assert abs(m_perfect - 0.10) < 0.001
    assert abs(m_risky - 0.20) < 0.001
    assert abs(m_failed - 0.30) < 0.001

    # 2. Test SLA Gates
    print("\n2. Testing SLA Gates (In-flight & Cooldown):")
    registry = WorkerRegistry(Path("test_workers.json"), max_inflight=2)
    wid = "test_worker_1"
    registry.workers[wid] = WorkerInfo(
        worker_id=wid,
        capabilities=[WorkerCapability(kind="test", cost=10)]
    )
    registry.save()
    
    print(f"  Initial eligibility: {registry.is_eligible(wid)}")
    assert registry.is_eligible(wid) is True
    
    # In-flight limit
    registry.record_job_start(wid)
    registry.record_job_start(wid)
    print(f"  After 2 jobs (max 2): {registry.is_eligible(wid)}")
    assert registry.is_eligible(wid) is False
    
    # Release one
    registry.record_worker_result(wid, 100, True)
    print(f"  After 1 result:       {registry.is_eligible(wid)}")
    assert registry.is_eligible(wid) is True
    
    # Cooldown (Simulate crash burst)
    for i in range(3):
        registry.record_worker_result(wid, 100, False)
        s = registry.workers[wid].stats
        print(f"    Failure {i+1}: consecutive={s.consecutive_failures} offline={s.is_offline}")

    print(f"  After 3 failures:     {registry.is_eligible(wid)} (Offline: {registry.workers[wid].stats.is_offline})")
    assert registry.is_eligible(wid) is False
    assert registry.workers[wid].stats.cooldown_until > time.time()

    print("\nPHASE 7 VERIFICATION SUCCESSFUL")

if __name__ == "__main__":
    test_governance()
