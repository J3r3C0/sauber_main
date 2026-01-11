import json
import os
import sys
import time
import logging
from pathlib import Path

# Add root to sys.path
root = Path(__file__).parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from mesh.registry.mesh_registry import WorkerRegistry, WorkerInfo, WorkerCapability
from mesh.registry.health_prober import HealthProber

# Enable logging to see selection decisions
logging.basicConfig(level=logging.INFO, format="%(name)s - %(levelname)s - %(message)s")

STORAGE = Path("runtime/test_hardening.json")

def setup_test():
    if STORAGE.exists(): STORAGE.unlink()
    if STORAGE.with_suffix(".json.bak").exists(): STORAGE.with_suffix(".json.bak").unlink()
    lock_file = STORAGE.with_suffix(".json.lock")
    if lock_file.exists(): lock_file.unlink()
    
    registry = WorkerRegistry(STORAGE)
    
    # Add a worker with a mock endpoint (localhost:9999)
    # Note: stats is initialized with defaults
    worker = WorkerInfo(
        worker_id="test_probe_worker",
        capabilities=[WorkerCapability(kind="test", cost=1)],
        endpoint="http://localhost:9999", # Will fail pings
        last_seen=time.time()
    )
    registry.register(worker)
    return registry

def test_prober_offline_gate():
    print("\n--- Testing Health Prober & Offline Gate ---")
    registry = setup_test()
    
    # Interval=0.3s, Threshold=2 for fast test
    prober = HealthProber(registry, interval_s=0.3)
    prober.fail_threshold = 2
    
    print("Starting prober... Expecting test_probe_worker to go offline after 2 fails.")
    prober.start()
    
    # Wait for enough ticks (0s, 0.3s, 0.6s, 0.9s)
    # Give it 2s to be very safe
    time.sleep(2.0)
    prober.stop()
    
    # Force reload to be sure we see disk state
    registry.load()
    
    worker = registry.get_worker("test_probe_worker")
    print(f"Worker status: is_offline={worker.stats.is_offline}, fails={worker.stats.consecutive_failures}")
    
    # Verify selection gate
    best = registry.get_best_worker("test")
    if best is None:
        print("Success: Offline worker was filtered out.")
        return True
    else:
        # Fallback check: is it actually filtered?
        if worker.stats.is_offline:
             print("Failure logic: get_best_worker selected an 'is_offline' worker!")
        else:
             print(f"Failure: Worker did not go offline (fails={worker.stats.consecutive_failures})")
        return False

def test_self_heal():
    print("\n--- Testing Self-Heal (.bak fallback) ---")
    registry = setup_test()
    registry.save() # Ensure primary exists
    
    # Manual backup creation (simulate atomic_io behavior)
    import shutil
    shutil.copy2(STORAGE, STORAGE.with_suffix(".json.bak"))
    
    # Corrupt primary
    with open(STORAGE, "w") as f:
        f.write("NOT JSON {CORRUPT}")
    
    print("Primary file corrupted. Attempting to load...")
    new_registry = WorkerRegistry(STORAGE)
    
    if "test_probe_worker" in new_registry.workers:
        print("Success: Recovered from .bak")
        # Check if primary was self-healed
        try:
            with open(STORAGE, "r") as f:
                json.load(f)
            print("Success: Primary file self-healed.")
            return True
        except:
            print("Failure: Primary file still corrupt.")
            return False
    else:
        print("Failure: Could not recover worker from .bak")
        return False

if __name__ == "__main__":
    os.makedirs("runtime", exist_ok=True)
    
    success = True
    if not test_prober_offline_gate(): success = False
    if not test_self_heal(): success = False
    
    if success:
        print("\nPHASE 3 VERIFICATION SUCCESSFUL")
    else:
        print("\nPHASE 3 VERIFICATION FAILED")
        sys.exit(1)
