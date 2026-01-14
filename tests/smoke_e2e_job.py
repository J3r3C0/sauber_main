# tests/smoke_e2e_job.py
"""Simple E2E test: Submit a read_file job and verify completion."""
import sys
import time
import uuid
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from core.database import get_db
from core import storage

def main():
    chain_id = f"smoke-{uuid.uuid4().hex[:8]}"
    task_id = f"smoke-task-{uuid.uuid4().hex[:8]}"
    spec_id = f"spec-{uuid.uuid4().hex[:8]}"
    
    print(f"[SMOKE] Creating chain spec for read_file job...")
    print(f"  Chain ID: {chain_id}")
    print(f"  Task ID: {task_id}")
    print(f"  Spec ID: {spec_id}")
    
    # Create task and chain spec in same transaction
    from core.models import Task
    from datetime import datetime
    
    # Create mission first
    from core.models import Mission
    mission = Mission(
        id="smoke-mission",
        title="Smoke Test Mission",
        description="E2E smoke test mission",
        user_id="smoke-user",
        status="active",
        metadata={},
        tags=[],
        created_at=datetime.utcnow().isoformat() + "Z"
    )
    # Only create if it doesn't exist
    existing_mission = storage.get_mission("smoke-mission")
    if not existing_mission:
        storage.create_mission(mission)
        print(f"[SMOKE] Mission created: smoke-mission")
    else:
        print(f"[SMOKE] Mission already exists: smoke-mission")
    
    # Create task
    task = Task(
        id=task_id,
        mission_id="smoke-mission",
        name="Smoke Test",
        description="E2E smoke test for read_file",
        kind="test",
        params={},
        created_at=datetime.utcnow().isoformat() + "Z"
    )
    storage.create_task(task)
    print(f"[SMOKE] Task created: {task_id}")
    
    # Now create chain context and specs
    with get_db() as conn:
        storage.ensure_chain_context(conn, chain_id, task_id)
        specs = [{
            "spec_id": spec_id,
            "kind": "read_file",
            "params": {"rel_path": "core/main.py"}
        }]
        storage.append_chain_specs(conn, chain_id, task_id, "root", "", specs)
        storage.set_chain_needs_tick(conn, chain_id, True)
        print(f"[SMOKE] Chain spec registered, needs_tick=True")
    
    # Wait for ChainRunner to process
    print(f"[SMOKE] Waiting 10s for ChainRunner to dispatch job...")
    time.sleep(10)
    
    # Check if job was created
    jobs = storage.list_jobs()
    chain_jobs = [j for j in jobs if j.payload.get("_chain_hint", {}).get("spec_id") == spec_id]
    
    if not chain_jobs:
        print(f"[SMOKE] ❌ FAIL: No job created for spec {spec_id}")
        return False
    
    job = chain_jobs[0]
    print(f"[SMOKE] ✅ Job created: {job.id}")
    print(f"  Status: {job.status}")
    print(f"  Kind: {job.payload.get('kind')}")
    print(f"  Depends on: {job.depends_on}")
    
    # CRITICAL: Validate root job has no dependencies
    if job.depends_on:
        print(f"[SMOKE] ❌ FAIL: Root job has dependencies: {job.depends_on}")
        return False
    print(f"[SMOKE] ✅ Root job has depends_on=[] (correct)")
    
    # Wait for completion
    print(f"[SMOKE] Waiting 15s for job completion...")
    time.sleep(15)
    
    # Check final status
    job_updated = storage.get_job(job.id)
    if not job_updated:
        print(f"[SMOKE] ❌ FAIL: Job {job.id} not found")
        return False
    
    print(f"[SMOKE] Final job status: {job_updated.status}")
    
    if job_updated.status == "completed":
        print(f"[SMOKE] ✅ PASS: Job completed successfully")
        if job_updated.result:
            content_len = len(str(job_updated.result.get("content", "")))
            print(f"  Result content length: {content_len} chars")
        return True
    else:
        print(f"[SMOKE] ❌ FAIL: Job status = {job_updated.status}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
