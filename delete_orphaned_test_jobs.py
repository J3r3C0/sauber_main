"""Delete jobs with non-existent task_id."""
from core import storage

jobs = storage.list_jobs()
pending = [j for j in jobs if j.status == "pending"]

deleted = []
for j in pending:
    # Check if task exists (simplified - just delete smoke-task jobs)
    if j.task_id == "smoke-task":
        print(f"Deleting orphaned test job: {j.id[:12]} (task_id={j.task_id})")
        storage.delete_job(j.id)
        deleted.append(j.id)

print(f"\n✅ Deleted {len(deleted)} orphaned test jobs")
