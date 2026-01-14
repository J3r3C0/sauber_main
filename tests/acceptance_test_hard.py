"""
Hard E2E Acceptance Test for Bug Fixes:
1. Schema breach fix (context_refs)
2. Storage AttributeError fix (file_blobs)

Creates ONE deterministic job and verifies:
- Job completes (status=done)
- decision_trace.jsonl updated NOW
- entry has state.context_refs
- no AttributeError
"""
import sys
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '.')

from core import storage
from core.models import Mission, Task, Job

def main():
    print("=" * 60)
    print("HARD E2E ACCEPTANCE TEST")
    print("=" * 60)
    
    # 1. Create mission/task (reuse if exists)
    mission = Mission(
        id="acceptance-test-mission",
        title="Acceptance Test",
        description="Hard E2E test for bug fixes",
        user_id="test-user",
        status="active",
        metadata={},
        tags=["acceptance"],
        created_at=datetime.utcnow().isoformat() + "Z"
    )
    
    if not storage.get_mission("acceptance-test-mission"):
        storage.create_mission(mission)
        print("[1/5] Mission created")
    else:
        print("[1/5] Mission exists")
    
    task = Task(
        id="acceptance-test-task",
        mission_id="acceptance-test-mission",
        name="Acceptance Test Task",
        description="Test task",
        kind="test",
        params={},
        created_at=datetime.utcnow().isoformat() + "Z"
    )
    
    if not storage.get_task("acceptance-test-task"):
        storage.create_task(task)
        print("[2/5] Task created")
    else:
        print("[2/5] Task exists")
    
    # 2. Create deterministic job
    job_id = f"acceptance-{int(time.time())}"
    job = Job(
        id=job_id,
        task_id="acceptance-test-task",
        payload={"kind": "read_file", "path": "core/main.py"},
        status="pending",
        priority="high",
        created_at=datetime.utcnow().isoformat() + "Z",
        updated_at=datetime.utcnow().isoformat() + "Z"
    )
    storage.create_job(job)
    print(f"[3/5] Job created: {job_id}")
    
    # 3. Wait for dispatch + completion
    print("[4/5] Waiting 25s for dispatch + completion...")
    time.sleep(25)
    
    # 4. Check job status
    job_final = storage.get_job(job_id)
    if not job_final:
        print(f"[5/5] ❌ FAIL: Job not found")
        return False
    
    print(f"[5/5] Job final status: {job_final.status}")
    
    # 5. Three Proofs
    print("\n" + "=" * 60)
    print("THREE PROOFS")
    print("=" * 60)
    
    # Proof 1: Job Status
    print(f"\n[PROOF 1] Job Status:")
    print(f"  ID: {job_final.id}")
    print(f"  Status: {job_final.status}")
    if job_final.result:
        print(f"  Result.ok: {job_final.result.get('ok', 'N/A')}")
        if 'error' in job_final.result:
            print(f"  Result.error: {job_final.result.get('error')}")
    
    # Proof 2: decision_trace.jsonl
    trace_file = Path("logs/decision_trace.jsonl")
    if trace_file.exists():
        stat = trace_file.stat()
        print(f"\n[PROOF 2] decision_trace.jsonl:")
        print(f"  Name: {trace_file.name}")
        print(f"  Length: {stat.st_size} bytes")
        print(f"  LastWriteTime: {datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Check last 2 entries
        with open(trace_file, 'r') as f:
            lines = f.readlines()
            if lines:
                print(f"\n  Last 2 entries:")
                import json
                for line in lines[-2:]:
                    entry = json.loads(line)
                    print(f"    - timestamp: {entry.get('timestamp')}")
                    print(f"      intent: {entry.get('intent')}")
                    print(f"      job_id: {entry.get('job_id')}")
                    print(f"      state.context_refs: {entry.get('state', {}).get('context_refs', 'MISSING')}")
    else:
        print(f"\n[PROOF 2] ❌ decision_trace.jsonl not found")
    
    # Proof 3: State Transitions (if exists)
    state_file = Path("logs/state_transitions.jsonl")
    if state_file.exists():
        print(f"\n[PROOF 3] state_transitions.jsonl exists")
    
    # Final Verdict
    print("\n" + "=" * 60)
    print("VERDICT")
    print("=" * 60)
    
    pass_criteria = {
        "Job completed": job_final.status in ["completed", "done"],
        "decision_trace updated": trace_file.exists() and (datetime.now().timestamp() - trace_file.stat().st_mtime) < 60,
        "context_refs present": False,  # Will check below
        "No AttributeError": 'AttributeError' not in str(job_final.result)
    }
    
    # Check context_refs in last entry
    if trace_file.exists():
        with open(trace_file, 'r') as f:
            lines = f.readlines()
            if lines:
                import json
                last_entry = json.loads(lines[-1])
                if 'context_refs' in last_entry.get('state', {}):
                    pass_criteria["context_refs present"] = True
    
    for criterion, passed in pass_criteria.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"  {status}: {criterion}")
    
    all_passed = all(pass_criteria.values())
    print("\n" + "=" * 60)
    if all_passed:
        print("✅ E2E ACCEPTANCE TEST PASSED")
    else:
        print("❌ E2E ACCEPTANCE TEST FAILED")
    print("=" * 60)
    
    return all_passed

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
