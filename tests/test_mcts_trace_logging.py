"""
Test: Verify MCTS trace logging by creating a job that goes through WebRelay/MCTS bridge.

This job will:
1. Create a mission/task/job
2. Dispatch through Dispatcher (which calls bridge.enqueue_job())
3. bridge.enqueue_job() injects mcts_trace into payload
4. Job completes and sync_job() logs to decision_trace.jsonl

PASS: decision_trace.jsonl gets a new entry with current timestamp
"""
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '.')

from core import storage
from core.models import Mission, Task, Job

def main():
    print("[MCTS_TRACE_TEST] Creating test job for MCTS trace verification...")
    
    # 1. Create mission
    mission = Mission(
        id="mcts-test-mission",
        title="MCTS Trace Test",
        description="Test to verify decision_trace.jsonl logging",
        user_id="test-user",
        status="active",
        metadata={},
        tags=["test"],
        created_at=datetime.utcnow().isoformat() + "Z"
    )
    
    existing = storage.get_mission("mcts-test-mission")
    if not existing:
        storage.create_mission(mission)
        print("[MCTS_TRACE_TEST] Mission created")
    else:
        print("[MCTS_TRACE_TEST] Mission already exists")
    
    # 2. Create task
    task = Task(
        id="mcts-test-task",
        mission_id="mcts-test-mission",
        name="MCTS Trace Test Task",
        description="Test task",
        kind="test",
        params={},
        created_at=datetime.utcnow().isoformat() + "Z"
    )
    existing_task = storage.get_task("mcts-test-task")
    if not existing_task:
        storage.create_task(task)
        print("[MCTS_TRACE_TEST] Task created")
    else:
        print("[MCTS_TRACE_TEST] Task already exists")
    
    # 3. Create job (kind=read_file to trigger WebRelay)
    job = Job(
        id=f"mcts-test-job-{int(time.time())}",
        task_id="mcts-test-task",
        payload={"kind": "read_file", "path": "core/main.py"},
        status="pending",
        priority="high",
        created_at=datetime.utcnow().isoformat() + "Z",
        updated_at=datetime.utcnow().isoformat() + "Z"
    )
    storage.create_job(job)
    print(f"[MCTS_TRACE_TEST] Job created: {job.id}")
    
    # 4. Check decision_trace.jsonl before
    trace_file = Path("logs/decision_trace.jsonl")
    before_mtime = trace_file.stat().st_mtime if trace_file.exists() else 0
    before_size = trace_file.stat().st_size if trace_file.exists() else 0
    
    print(f"[MCTS_TRACE_TEST] decision_trace.jsonl before:")
    print(f"  mtime: {datetime.fromtimestamp(before_mtime) if before_mtime else 'N/A'}")
    print(f"  size: {before_size} bytes")
    
    # 5. Wait for Dispatcher to dispatch and Worker to complete
    print("[MCTS_TRACE_TEST] Waiting 20s for job dispatch + completion...")
    time.sleep(20)
    
    # 6. Check job status
    job_updated = storage.get_job(job.id)
    if job_updated:
        print(f"[MCTS_TRACE_TEST] Job status: {job_updated.status}")
        if "mcts_trace" in job_updated.payload:
            print(f"[MCTS_TRACE_TEST] ✅ mcts_trace exists in payload")
        else:
            print(f"[MCTS_TRACE_TEST] ❌ mcts_trace NOT in payload")
    else:
        print(f"[MCTS_TRACE_TEST] ❌ Job not found")
    
    # 7. Check decision_trace.jsonl after
    after_mtime = trace_file.stat().st_mtime if trace_file.exists() else 0
    after_size = trace_file.stat().st_size if trace_file.exists() else 0
    
    print(f"\n[MCTS_TRACE_TEST] decision_trace.jsonl after:")
    print(f"  mtime: {datetime.fromtimestamp(after_mtime) if after_mtime else 'N/A'}")
    print(f"  size: {after_size} bytes")
    
    # 8. Verdict
    if after_mtime > before_mtime:
        print(f"\n[MCTS_TRACE_TEST] ✅ PASS: decision_trace.jsonl was updated!")
        print(f"  Size increased by {after_size - before_size} bytes")
        
        # Show last entry
        with open(trace_file, 'r') as f:
            lines = f.readlines()
            if lines:
                print(f"\n  Last entry:")
                import json
                last = json.loads(lines[-1])
                print(f"    timestamp: {last.get('timestamp')}")
                print(f"    intent: {last.get('intent')}")
                print(f"    job_id: {last.get('job_id')}")
        return True
    else:
        print(f"\n[MCTS_TRACE_TEST] ❌ FAIL: decision_trace.jsonl was NOT updated")
        print(f"  Possible causes:")
        print(f"    - Job not dispatched (check Dispatcher)")
        print(f"    - Job not completed (check Worker)")
        print(f"    - mcts_trace not in payload (check bridge.enqueue_job)")
        print(f"    - trace_logger.log_node() not called (check main.py sync_job)")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
