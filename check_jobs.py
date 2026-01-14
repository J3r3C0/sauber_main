from core import storage

jobs = storage.list_jobs()
print(f"Total jobs: {len(jobs)}")

pending = [j for j in jobs if j.status == "pending"]
print(f"Pending jobs: {len(pending)}")

print("\nRecent 5 jobs:")
for j in jobs[-5:]:
    print(f"  {j.id[:12]} - {j.status} - {j.payload.get('kind', 'unknown')}")
