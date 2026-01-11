import json
import multiprocessing as mp
import os
import random
import time
import sys
from pathlib import Path

# Add root to sys.path
root = Path(__file__).parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from core.utils.atomic_io import atomic_write_json

PATH = "runtime/test_state.json"

def worker(idx: int):
    print(f"[worker-{idx}] starting stress test...")
    for i in range(100):
        state = {
            "worker": idx,
            "i": i,
            "rand": random.random(),
            "timestamp": time.time()
        }
        try:
            atomic_write_json(PATH, state)
        except Exception as e:
            print(f"[worker-{idx}] ERROR: {e}")
        # Very small sleep to encourage context switching / races
        time.sleep(random.random() * 0.005)

if __name__ == "__main__":
    # Ensure runtime dir exists
    os.makedirs("runtime", exist_ok=True)
    
    # Start processes
    procs = [mp.Process(target=worker, args=(i,)) for i in range(4)]
    print(f"Starting {len(procs)} parallel workers...")
    
    start_time = time.time()
    for p in procs: p.start()
    for p in procs: p.join()
    duration = time.time() - start_time
    
    print(f"Stress test finished in {duration:.2f}s")

    # Validation
    try:
        with open(PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
            print(f"Validation OK: JSON is valid. Last state: {data}")
    except json.JSONDecodeError as e:
        print(f"CRITICAL ERROR: JSON is corrupt! {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error during validation: {e}")
        sys.exit(1)

    # Check for .bak
    if os.path.exists(PATH + ".bak"):
        print(f"Backup file found: {PATH}.bak")
    else:
        print("Warning: Backup file not found (might be expected if first run)")

    print("STRESS TEST SUCCESSFUL")
