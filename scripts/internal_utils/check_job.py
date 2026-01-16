import sys
import json
from core import storage

job_id = sys.argv[1] if len(sys.argv) > 1 else None
if not job_id:
    print("Usage: python check_job.py <job_id>")
    sys.exit(1)

job = storage.get_job(job_id)
if not job:
    print(f"Job {job_id} not found")
    sys.exit(1)

print(json.dumps(job.model_dump(), indent=2, default=str))
