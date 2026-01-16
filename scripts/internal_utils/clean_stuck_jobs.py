"""Mark stuck working jobs as failed to unblock rate limiter."""
from core import storage
from datetime import datetime

jobs = storage.list_jobs()
working = [j for j in jobs if j.status == "working"]

stuck = []
for j in working:
    try:
        created = datetime.fromisoformat(j.created_at.replace('Z', '+00:00'))
        age_seconds = (datetime.now(created.tzinfo) - created).total_seconds()
        if age_seconds > 300:  # 5 minutes
            stuck.append((j, age_seconds))
    except:
        pass

if not stuck:
    print("✅ No stuck jobs to clean")
else:
    print(f"Found {len(stuck)} stuck working jobs (>5min)")
    print("Marking as failed to unblock rate limiter...")
    
    for j, age in stuck:
        j.status = "failed"
        j.result = {"ok": False, "error": f"Job stuck in working for {int(age)}s, marked as failed"}
        j.updated_at = datetime.utcnow().isoformat() + "Z"
        storage.update_job(j)
        print(f"  {j.id[:12]} - {(j.payload or {}).get('kind')} - {int(age)}s → failed")
    
    print(f"\n✅ Marked {len(stuck)} stuck jobs as failed")
    print("Rate limiter should now allow new dispatches")
