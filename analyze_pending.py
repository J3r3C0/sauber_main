"""Analyze pending jobs to determine if blocked by dependencies or dispatcher issue."""
from core import storage

jobs = storage.list_jobs()
by_id = {j.id: j for j in jobs}

pending = [j for j in jobs if j.status == "pending"]

def is_blocked(j):
    """Check if job is blocked by incomplete dependencies."""
    return any(dep_id in by_id and by_id[dep_id].status != "completed" for dep_id in (j.depends_on or []))

blocked = [j for j in pending if (j.depends_on and is_blocked(j))]
unblocked = [j for j in pending if not (j.depends_on and is_blocked(j))]

print(f"Total pending: {len(pending)}")
print(f"Blocked by dependencies: {len(blocked)}")
print(f"Unblocked (dispatcher issue): {len(unblocked)}")

if unblocked:
    print(f"\n⚠️ {len(unblocked)} unblocked pending jobs (should be dispatched):")
    for j in unblocked[:5]:
        print(f"  {j.id[:12]} - {(j.payload or {}).get('kind')} - depends_on={j.depends_on}")
else:
    print("\n✅ All pending jobs are correctly blocked by dependencies")

if blocked:
    print(f"\nℹ️ {len(blocked)} jobs blocked by dependencies (normal):")
    for j in blocked[:3]:
        deps_status = [(dep_id[:12], by_id[dep_id].status) for dep_id in (j.depends_on or []) if dep_id in by_id]
        print(f"  {j.id[:12]} waiting for: {deps_status}")
