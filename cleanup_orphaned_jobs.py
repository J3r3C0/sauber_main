"""Cleanup all orphaned jobs (jobs without valid task/mission)"""
from core.database import get_db
from core import storage

print("Cleaning up orphaned jobs...")

jobs = storage.list_jobs()
orphaned = []

for job in jobs:
    # Check if task exists
    task = storage.get_task(job.task_id)
    if not task:
        orphaned.append(job.id)
        print(f"  Orphaned job (no task): {job.id[:12]} (task_id={job.task_id})")
        continue
    
    # Check if mission exists
    if task.mission_id:
        mission = storage.get_mission(task.mission_id)
        if not mission:
            orphaned.append(job.id)
            print(f"  Orphaned job (no mission): {job.id[:12]} (mission_id={task.mission_id})")

if orphaned:
    with get_db() as conn:
        for job_id in orphaned:
            conn.execute(
                "UPDATE jobs SET status='failed', updated_at=datetime('now') WHERE id=?",
                (job_id,)
            )
        conn.commit()
    print(f"\n✅ Marked {len(orphaned)} orphaned jobs as failed")
else:
    print("\n✅ No orphaned jobs found")
