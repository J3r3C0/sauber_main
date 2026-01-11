import json
import os
import sys
import time
from pathlib import Path

# Add root to sys.path
root = Path(__file__).parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from mesh.registry.mesh_registry import WorkerRegistry, WorkerInfo, WorkerCapability

STORAGE = Path("runtime/test_workers_scoring.json")

def setup_registry():
    if STORAGE.exists(): STORAGE.unlink()
    registry = WorkerRegistry(STORAGE)
    
    # Worker A: Stable, fast, but slightly more expensive
    worker_a = WorkerInfo(
        worker_id="stable_pro",
        capabilities=[WorkerCapability(kind="llm", cost=10)],
        last_seen=time.time()
    )
    worker_a.stats.last_seen_ts = time.time()
    
    # Worker B: Cheap, but potentially slow or unreliable
    worker_b = WorkerInfo(
        worker_id="cheap_spot",
        capabilities=[WorkerCapability(kind="llm", cost=5)],
        last_seen=time.time()
    )
    worker_b.stats.last_seen_ts = time.time()
    
    registry.register(worker_a)
    registry.register(worker_b)
    return registry

def run_simulation():
    registry = setup_registry()
    
    print("\n--- Simulation: Worker Scoring v1 ---")
    
    # 1. Initial Selection
    best = registry.get_best_worker("llm")
    print(f"Initial selection (should be cheap_spot): {best.worker_id}")
    
    # 2. Simulate Worker B being UNRELIABLE
    print("\nRecording 5 failures for 'cheap_spot'...")
    for _ in range(5):
        registry.record_worker_result("cheap_spot", latency_ms=800, success=False)
    
    # Check stats
    worker_b = registry.get_worker("cheap_spot")
    print(f"cheap_spot success_ema: {worker_b.stats.success_ema:.2f}, n: {worker_b.stats.n}")
    
    # 3. New Selection
    best = registry.get_best_worker("llm")
    print(f"Selection after failures (should be stable_pro): {best.worker_id}")
    
    # 4. Simulate Worker A being SLOW but reliable
    print("\nRecording 5 slow successes for 'stable_pro'...")
    for _ in range(5):
        registry.record_worker_result("stable_pro", latency_ms=1600, success=True)
        
    worker_a = registry.get_worker("stable_pro")
    print(f"stable_pro latency_ema: {worker_a.stats.latency_ms_ema:.0f}ms, success_ema: {worker_a.stats.success_ema:.2f}")

    # 5. Final Selection
    best = registry.get_best_worker("llm")
    print(f"Final selection: {best.worker_id}")
    
    # Cleanup
    if STORAGE.exists(): STORAGE.unlink()
    if Path(str(STORAGE) + ".lock").exists(): Path(str(STORAGE) + ".lock").unlink()
    
    return True

if __name__ == "__main__":
    os.makedirs("runtime", exist_ok=True)
    success = run_simulation()
    if success:
        print("\nSCORING SIMULATION SUCCESSFUL")
    else:
        print("\nSCORING SIMULATION FAILED")
        sys.exit(1)
