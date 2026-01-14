"""Mark orphaned test jobs as failed."""
from core import storage
from datetime import datetime

jobs = storage.list_jobs()
pending = [j for j in jobs if j.status == "pending"]

marked = []
for j in pending:
    if j.task_id == "smoke-task":
        print(f"Marking orphaned test job as failed: {j.id[:12]} (task_id={j.task_id})")
        j.status = "failed"
        j.result = {"ok": False, "error": "Task not found (orphaned test job)"}
        j.updated_at = datetime.utcnow().isoformat() + "Z"
        storage.update_job(j)
        marked.append(j.id)

print(f"\n✅ Marked {len(marked)} orphaned test jobs as failed")
