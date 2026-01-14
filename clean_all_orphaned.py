# Clean all orphaned jobs (including 'root' dependencies)
from core import storage
from datetime import datetime

jobs = storage.list_jobs()
pending = [j for j in jobs if j.status == "pending"]

fixed_count = 0
for j in pending:
    if j.depends_on:
        # Check if all dependencies exist
        all_exist = all(any(job.id == dep_id for job in jobs) for dep_id in j.depends_on)
        if not all_exist:
            print(f"Fixing job {j.id[:12]}: removing invalid dependencies {j.depends_on}")
            j.depends_on = []
            j.updated_at = datetime.utcnow().isoformat() + "Z"
            storage.update_job(j)
            fixed_count += 1

print(f"\n✅ Fixed {fixed_count} jobs with invalid dependencies")
