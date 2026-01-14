# Fix orphaned jobs by clearing invalid dependencies
from core import storage
from datetime import datetime

jobs = storage.list_jobs()
pending = [j for j in jobs if j.status == "pending"]

fixed_count = 0
for j in pending:
    if j.depends_on and j.depends_on == ['parent']:
        # Check if parent exists
        parent_exists = any(job.id == 'parent' for job in jobs)
        if not parent_exists:
            print(f"Fixing job {j.id[:12]}: removing invalid dependency 'parent'")
            j.depends_on = []
            j.updated_at = datetime.utcnow().isoformat() + "Z"
            storage.update_job(j)
            fixed_count += 1

print(f"\n✅ Fixed {fixed_count} jobs with invalid dependencies")
