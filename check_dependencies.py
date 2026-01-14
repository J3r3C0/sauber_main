# Check job dependencies
from core import storage

jobs = storage.list_jobs()
pending = [j for j in jobs if j.status == "pending"]

print(f"Total pending jobs: {len(pending)}\n")

for j in pending[:5]:  # Show first 5
    print(f"Job {j.id[:12]}")
    print(f"  Kind: {j.payload.get('kind', 'unknown')}")
    print(f"  Depends on: {j.depends_on}")
    if j.depends_on:
        for dep_id in j.depends_on:
            dep_job = storage.get_job(dep_id)
            if dep_job:
                print(f"    - {dep_id[:12]}: status={dep_job.status}")
            else:
                print(f"    - {dep_id[:12]}: NOT FOUND ❌")
    print()
