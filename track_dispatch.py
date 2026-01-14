# Check dispatch pipeline
from core import storage
import time

# Find a pending job with no dependencies
jobs = storage.list_jobs()
pending_ready = [j for j in jobs if j.status == "pending" and not j.depends_on]

if not pending_ready:
    print("❌ No pending jobs with depends_on=[]")
    exit(1)

job = pending_ready[0]
print(f"Tracking job: {job.id[:12]}")
print(f"  Kind: {job.payload.get('kind')}")
print(f"  Status: {job.status}")
print(f"  Depends on: {job.depends_on}")

# Wait 10 seconds for dispatcher
print("\nWaiting 10s for dispatcher...")
time.sleep(10)

# Check if status changed
job_updated = storage.get_job(job.id)
print(f"\nAfter 10s:")
print(f"  Status: {job_updated.status}")

if job_updated.status == "working":
    print("✅ Dispatcher dispatched job (pending → working)")
elif job_updated.status == "pending":
    print("❌ Dispatcher did NOT dispatch job (still pending)")
    print("\nCheck Core logs for:")
    print(f"  [dispatcher] 🚀 Dispatching job {job.id[:8]}")
else:
    print(f"⚠️ Unexpected status: {job_updated.status}")
