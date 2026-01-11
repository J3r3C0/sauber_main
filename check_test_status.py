import requests
import json

# Get recent jobs
jobs = requests.get('http://localhost:8001/api/jobs').json()
print(f'\nTotal jobs: {len(jobs)}')

# Show 5 most recent
recent = sorted(jobs, key=lambda x: x.get('created_at', ''), reverse=True)[:5]
print('\nRecent jobs:')
for j in recent:
    job_id = j['id'][:12]
    status = j.get('status', '?')
    kind = j.get('payload', {}).get('kind', '?')
    result = j.get('result') or {}
    result_ok = result.get('ok', '?') if isinstance(result, dict) else '?'
    print(f'  {job_id}: {status:10} kind={kind:15} ok={result_ok}')

# Check for agent_plan jobs
agent_plans = [j for j in jobs if j.get('payload', {}).get('kind') == 'agent_plan']
print(f'\nAgent plan jobs: {len(agent_plans)}')
if agent_plans:
    latest = agent_plans[-1]
    print(f'  Latest: {latest["id"][:12]} - {latest.get("status")}')
    if latest.get('result'):
        print(f'  Result keys: {list(latest["result"].keys())}')
