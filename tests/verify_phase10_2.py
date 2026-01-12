# tests/verify_phase10_2.py
import sys
import os
import time
import uuid
import logging
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add root project to path
sys.path.append(str(Path(__file__).parent.parent))

from core.database import get_db, init_db
from core import storage
from core.chain_runner import ChainRunner

# Configure logging to stdout for debugging
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format='%(levelname)s:%(name)s:%(message)s')

def test_1_async_dispatch_flow():
    print("\n--- TEST 1: Async Dispatch Flow ---")
    chain_id = f"c1-{uuid.uuid4().hex[:4]}"
    task_id = "task-1"
    spec1_id = f"s1-{uuid.uuid4().hex[:4]}"
    
    with get_db() as conn:
        storage.ensure_chain_context(conn, chain_id, task_id)
        # Register a spec
        specs = [{"spec_id": spec1_id, "kind": "test_job", "params": {"foo": "bar"}}]
        storage.append_chain_specs(conn, chain_id, task_id, "root", "parent", specs)
        storage.set_chain_needs_tick(conn, chain_id, True)
    
    runner = ChainRunner(poll_interval_sec=0.1)
    
    # Run one tick
    print("Running runner.tick()...")
    count = runner.tick()
    assert count == 1
    
    with get_db() as conn:
        # Check spec status
        pending = storage.list_pending_chain_specs(conn, chain_id)
        assert len(pending) == 0
        
        # Verify job was created
        jobs = storage.list_jobs()
        chain_jobs = [j for j in jobs if j.payload.get("_chain_hint", {}).get("spec_id") == spec1_id]
        assert len(chain_jobs) == 1
        print(f"Dispatched Job ID: {chain_jobs[0].id} [PASS]")
        
    print("TEST 1 PASSED")

def test_2_lease_expiry_and_retry():
    print("\n--- TEST 2: Lease Expiry and Retry ---")
    chain_id = f"c2-{uuid.uuid4().hex[:4]}"
    task_id = "task-2"
    spec2_id = f"s2-{uuid.uuid4().hex[:4]}"
    
    # 1. Create spec and claim it manually with a short lease
    with get_db() as conn:
        storage.ensure_chain_context(conn, chain_id, task_id)
        storage.append_chain_specs(conn, chain_id, task_id, "root", "parent", [{"spec_id": spec2_id, "kind": "retry_test", "params": {}}])
        
        # Explicit claim with short lease
        spec = storage.claim_next_pending_spec(conn, chain_id, lease_seconds=1)
        assert spec is not None
        print(f"Claimed spec: {spec['spec_id']} until {spec['claimed_until']}")
        
    # 2. Try to claim again immediately (should fail)
    with get_db() as conn:
        # Same chain_id, it's already leased
        spec_again = storage.claim_next_pending_spec(conn, chain_id, lease_seconds=10)
        assert spec_again is None
        print("Second claim attempt failed (correctly leased)")
        
    # 3. Wait for lease to expire
    print("Waiting 1.5s for lease expiry...")
    time.sleep(1.5)
    
    # 4. Try to claim again (should succeed)
    with get_db() as conn:
        spec_retry = storage.claim_next_pending_spec(conn, chain_id, lease_seconds=10)
        assert spec_retry is not None
        print(f"Re-claimed spec: {spec_retry['spec_id']} (Retry Successful)")
        
    print("TEST 2 PASSED")

def test_3_multi_runner_concurrency_fix():
    print("\n--- TEST 3: Multi-Runner Concurrency (Fix) ---")
    chain_id = f"c3-{uuid.uuid4().hex[:4]}"
    task_id = "task-3"
    
    # Clear tables for clean check
    with get_db() as conn:
        conn.execute("DELETE FROM jobs")
        conn.execute("DELETE FROM chain_specs")
        conn.execute("DELETE FROM chain_context")
        conn.commit()

    # 1. Create 5 specs with UNIQUE params to avoid deduplication
    print("Registering 5 unique specs...")
    with get_db() as conn:
        storage.ensure_chain_context(conn, chain_id, task_id)
        specs = [{"spec_id": f"x{i}-{uuid.uuid4().hex[:4]}", "kind": "job", "params": {"i": i}} for i in range(5)]
        storage.append_chain_specs(conn, chain_id, task_id, "root", "parent", specs)
        storage.set_chain_needs_tick(conn, chain_id, True)
    
    # Initialize 2 runners
    r1 = ChainRunner()
    r2 = ChainRunner()
    
    # Simulate racing ticks
    # Since each tick processes 1 spec per chain, we need 5 ticks total
    print("Simulating racing runners...")
    c1 = r1.tick(); print(f"Tick 1 r1: processed {c1}")
    c2 = r2.tick(); print(f"Tick 2 r2: processed {c2}")
    c3 = r1.tick(); print(f"Tick 3 r1: processed {c3}")
    c4 = r2.tick(); print(f"Tick 4 r2: processed {c4}")
    c5 = r1.tick(); print(f"Tick 5 r1: processed {c5}")
    
    with get_db() as conn:
        # Total jobs should be exactly 5
        jobs = storage.list_jobs()
        chain_jobs = [j for j in jobs if j.payload.get("_chain_hint", {}).get("chain_id") == chain_id]
        print(f"ACTUAL COUNT: {len(chain_jobs)}")
        assert len(chain_jobs) == 5
        
        # No pending specs left
        pending = storage.list_pending_chain_specs(conn, chain_id)
        assert len(pending) == 0
        
    print("TEST 3 PASSED")

if __name__ == "__main__":
    init_db()
    try:
        test_1_async_dispatch_flow()
        test_2_lease_expiry_and_retry()
        test_3_multi_runner_concurrency_fix()
        print("\nALL PHASE 10.2 VERIFICATION TESTS PASSED!")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
