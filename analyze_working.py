"""Analyze working jobs to identify stuck jobs."""
from core import storage
from datetime import datetime

jobs = storage.list_jobs()
working = [j for j in jobs if j.status == "working"]

print(f"Total working jobs: {len(working)}")

if not working:
    print("✅ No working jobs (all completed or pending)")
else:
    # Sort by created_at to find oldest
    working_sorted = sorted(working, key=lambda j: j.created_at or "")
    
    print(f"\nOldest 5 working jobs:")
    for j in working_sorted[:5]:
        # Calculate age
        try:
            created = datetime.fromisoformat(j.created_at.replace('Z', '+00:00'))
            age_seconds = (datetime.now(created.tzinfo) - created).total_seconds()
            age_str = f"{int(age_seconds)}s"
        except:
            age_str = "unknown"
        
        print(f"  {j.id[:12]} - {(j.payload or {}).get('kind')} - age={age_str}")
    
    # Check for very old jobs (>5 minutes)
    stuck = []
    for j in working:
        try:
            created = datetime.fromisoformat(j.created_at.replace('Z', '+00:00'))
            age_seconds = (datetime.now(created.tzinfo) - created).total_seconds()
            if age_seconds > 300:  # 5 minutes
                stuck.append((j, age_seconds))
        except:
            pass
    
    if stuck:
        print(f"\n⚠️ {len(stuck)} jobs stuck in working (>5min):")
        for j, age in stuck[:5]:
            print(f"  {j.id[:12]} - {(j.payload or {}).get('kind')} - {int(age)}s")
        print("\nCheck worker logs for these job IDs")
    else:
        print("\n✅ No stuck jobs (all working jobs < 5min old)")
