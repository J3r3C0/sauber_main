# Quick check: Is dispatcher running?
import time
from core import storage

print("Checking dispatcher activity...")
print(f"Time: {time.strftime('%H:%M:%S')}")

jobs_before = len([j for j in storage.list_jobs() if j.status == "pending"])
print(f"Pending jobs before: {jobs_before}")

print("Waiting 5 seconds for dispatcher tick...")
time.sleep(5)

jobs_after = len([j for j in storage.list_jobs() if j.status == "pending"])
working = len([j for j in storage.list_jobs() if j.status == "working"])
print(f"Pending jobs after: {jobs_after}")
print(f"Working jobs: {working}")

if jobs_before > jobs_after or working > 0:
    print("✅ Dispatcher is ACTIVE (jobs moved to working)")
else:
    print("❌ Dispatcher seems INACTIVE (no status changes)")
