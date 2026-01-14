from core import storage

jobs = storage.list_jobs()
print(f"Total jobs: {len(jobs)}")
print(f"Pending: {len([j for j in jobs if j.status == 'pending'])}")
print(f"Working: {len([j for j in jobs if j.status == 'working'])}")
print(f"Completed: {len([j for j in jobs if j.status == 'completed'])}")
print(f"Failed: {len([j for j in jobs if j.status == 'failed'])}")

# Check latest job
latest = jobs[-1] if jobs else None
if latest:
    print(f"\nLatest job: {latest.id[:12]}")
    print(f"  Status: {latest.status}")
    print(f"  Kind: {latest.payload.get('kind')}")
    print(f"  Depends on: {latest.depends_on}")
