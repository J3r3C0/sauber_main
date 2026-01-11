import requests
import json

# Get recent failed agent_plan job
jobs = requests.get('http://localhost:8001/api/jobs').json()
agent_plans = [j for j in jobs if j.get('payload', {}).get('kind') == 'agent_plan']
failed = [j for j in agent_plans if j.get('status') == 'failed']

if failed:
    latest = failed[-1]
    print(f"Latest failed agent_plan job: {latest['id'][:12]}")
    print(f"Status: {latest.get('status')}")
    
    result = latest.get('result', {})
    print(f"\nResult:")
    print(json.dumps(result, indent=2))
else:
    print("No failed agent_plan jobs found")
