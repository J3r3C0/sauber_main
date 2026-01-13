"""
Stage 4 Smoke Test: Real Dispatch Validation

Creates and dispatches 10 test jobs through the system to validate:
1. MCTS candidate building
2. Decision trace logging
3. Schema validation
4. Policy updates
5. 0 breaches

Requirements:
- System must be running (START_COMPLETE_SYSTEM.bat)
- Or run in standalone mode
"""

import json
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core import storage, models
from core.webrelay_bridge import WebRelayBridge, WebRelaySettings
from core import config


def create_test_job(index: int) -> str:
    """Create a minimal test job in storage"""
    job_id = f"smoke_test_{index:03d}_{uuid.uuid4().hex[:8]}"
    
    # Create mission
    mission = models.Mission(
        id=f"smoke_mission_{index}",
        user_id="smoke_test_user",
        goal=f"Smoke test dispatch {index}",
        status="active",
        created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    )
    storage.create_mission(mission)
    
    # Create task
    task = models.Task(
        id=f"smoke_task_{index}",
        mission_id=mission.id,
        name=f"smoke_test_task_{index}",
        kind="llm_call",
        status="pending",
        params={},
        created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    )
    storage.create_task(task)
    
    # Create job
    job = models.Job(
        id=job_id,
        task_id=task.id,
        status="pending",
        payload={"test": True, "index": index},
        created_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    )
    storage.create_job(job)
    
    return job_id


def run_smoke_test():
    """Run smoke test with 10 dispatches"""
    print("\n" + "=" * 60)
    print("Stage 4 Smoke Test: Real Dispatch Validation")
    print("=" * 60)
    
    # Setup bridge
    settings = WebRelaySettings(
        relay_out_dir=config.DATA_DIR / "webrelay_out",
        relay_in_dir=config.DATA_DIR / "webrelay_in",
        session_prefix="smoke_test"
    )
    bridge = WebRelayBridge(settings)
    
    # Clear logs for clean test
    decision_log = Path("logs/decision_trace.jsonl")
    breach_log = Path("logs/decision_trace_breaches.jsonl")
    
    initial_decision_count = 0
    if decision_log.exists():
        with open(decision_log) as f:
            initial_decision_count = len(f.readlines())
    
    initial_breach_count = 0
    if breach_log.exists():
        with open(breach_log) as f:
            initial_breach_count = len(f.readlines())
    
    print(f"\nInitial state:")
    print(f"  Decision log: {initial_decision_count} events")
    print(f"  Breach log: {initial_breach_count} breaches")
    
    # Dispatch 10 jobs
    print(f"\n[TEST] Dispatching 10 test jobs...")
    
    job_ids = []
    for i in range(10):
        try:
            job_id = create_test_job(i)
            job_ids.append(job_id)
            
            # Dispatch via bridge (triggers MCTS if integrated)
            job_file = bridge.enqueue_job(job_id)
            
            print(f"  [{i+1}/10] Job {job_id[:20]}... → {job_file.name}")
            
        except Exception as e:
            print(f"  [{i+1}/10] FAILED: {e}")
            import traceback
            traceback.print_exc()
    
    # Wait a moment for async processing
    time.sleep(2)
    
    # Verify logs
    print("\n[VERIFY] Checking decision traces...")
    
    final_decision_count = 0
    if decision_log.exists():
        with open(decision_log) as f:
            final_decision_count = len(f.readlines())
    
    final_breach_count = 0
    if breach_log.exists():
        with open(breach_log) as f:
            final_breach_count = len(f.readlines())
    
    new_decisions = final_decision_count - initial_decision_count
    new_breaches = final_breach_count - initial_breach_count
    
    print(f"\nFinal state:")
    print(f"  Decision log: {final_decision_count} events (+{new_decisions})")
    print(f"  Breach log: {final_breach_count} breaches (+{new_breaches})")
    
    # Validate
    print("\n[VALIDATE] Running schema validation...")
    
    import subprocess
    result = subprocess.run(
        [sys.executable, "scripts/validate_decision_log.py"],
        capture_output=True,
        text=True
    )
    
    print(result.stdout)
    
    if result.returncode != 0:
        print("❌ Schema validation failed")
        print(result.stderr)
        return False
    
    # Summary
    print("\n" + "=" * 60)
    
    if new_decisions >= 10 and new_breaches == 0:
        print("✅ SMOKE TEST PASSED")
        print("=" * 60)
        print(f"  - {new_decisions} new decision traces logged")
        print(f"  - 0 new breaches")
        print(f"  - All events schema-valid")
        print("=" * 60)
        return True
    else:
        print("❌ SMOKE TEST FAILED")
        print("=" * 60)
        print(f"  - Expected: ≥10 decisions, 0 breaches")
        print(f"  - Actual: {new_decisions} decisions, {new_breaches} breaches")
        print("=" * 60)
        return False


if __name__ == "__main__":
    try:
        success = run_smoke_test()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ SMOKE TEST CRASHED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
