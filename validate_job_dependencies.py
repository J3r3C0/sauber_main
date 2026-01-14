# validate_job_dependencies.py
"""Validate that all job dependencies reference existing jobs."""
from core import storage

jobs = storage.list_jobs()
job_ids = {j.id for j in jobs}

invalid = []
for j in jobs:
    for dep_id in (j.depends_on or []):
        if dep_id not in job_ids:
            invalid.append((j.id, dep_id))

if invalid:
    print(f"❌ {len(invalid)} jobs with invalid dependencies:")
    for job_id, dep_id in invalid[:20]:
        print(f"  {job_id[:12]} depends on {dep_id} (NOT FOUND)")
    raise SystemExit(1)
else:
    print("✅ All job dependencies are valid")
