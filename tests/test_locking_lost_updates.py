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

from core.utils.atomic_io import atomic_write_json, json_lock

PATH = "runtime/counter.json"

def increment_worker(idx: int, use_lock: bool, iterations: int):
    print(f"[worker-{idx}] starting (use_lock={use_lock})...")
    for _ in range(iterations):
        if use_lock:
            with json_lock(PATH):
                # READ
                if os.path.exists(PATH):
                    with open(PATH, "r", encoding="utf-8") as f:
                        data = json.load(f)
                else:
                    data = {"count": 0}
                
                # MODIFY
                data["count"] += 1
                
                # WRITE (Atomic)
                atomic_write_json(PATH, data)
        else:
            # NO LOCK (Race condition expected)
            if os.path.exists(PATH):
                with open(PATH, "r", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                data = {"count": 0}
            
            data["count"] += 1
            atomic_write_json(PATH, data)
        
        # Jitter to increase race probability
        time.sleep(random.uniform(0, 0.001))

def run_test(use_lock: bool):
    if os.path.exists(PATH): os.remove(PATH)
    if os.path.exists(PATH + ".lock"): os.remove(PATH + ".lock")
    
    num_procs = 4
    iterations = 50
    total_expected = num_procs * iterations
    
    print(f"\n--- Testing Lost Updates (Locking={use_lock}) ---")
    procs = [mp.Process(target=increment_worker, args=(i, use_lock, iterations)) for i in range(num_procs)]
    
    for p in procs: p.start()
    for p in procs: p.join()
    
    with open(PATH, "r", encoding="utf-8") as f:
        final_data = json.load(f)
        final_count = final_data["count"]
    
    print(f"Expected: {total_expected}, Got: {final_count}")
    return final_count == total_expected

if __name__ == "__main__":
    os.makedirs("runtime", exist_ok=True)
    
    # Test WITHOUT lock
    print("Testing without lock (expecting failure/race)...")
    success_no_lock = run_test(use_lock=False)
    
    # Test WITH lock
    print("\nTesting with lock (expecting success)...")
    success_with_lock = run_test(use_lock=True)
    
    if not success_no_lock:
        print("\nRace condition confirmed (without lock).")
    else:
        print("\nWarning: No race condition detected without lock (try increasing iterations/procs).")
        
    if success_with_lock:
        print("LOST UPDATE PREVENTION VERIFIED (with lock).")
    else:
        print("CRITICAL: LOCKING FAILED TO PREVENT LOST UPDATES.")
        sys.exit(1)
