# Phase 9 E2E Test 1: Single-Step Chain (walk_tree)
# Tests: walk_tree capability, deterministic output, basic chain creation

import requests
import json
import time

BASE_URL = "http://localhost:8001"

print("=== Phase 9 Test 1: Single-Step Chain (walk_tree) ===\n")

# 1. Create Mission
print("1. Creating mission...")
resp = requests.post(f"{BASE_URL}/api/missions", json={
    "title": "Test Walk Tree",
    "description": "List Python files in core/ directory"
})
resp.raise_for_status()
mission = resp.json()
mission_id = mission["id"]
print(f"   ✓ Mission created: {mission_id[:12]}...\n")

# 2. Create agent_plan Task
print("2. Creating agent_plan task...")
resp = requests.post(f"{BASE_URL}/api/missions/{mission_id}/tasks", json={
    "name": "Walk core directory",
    "kind": "agent_plan",
    "params": {
        "user_prompt": "Use walk_tree to list all .py files in the core/ directory. Return the file list as your final answer.",
        "chain_id": f"test_walk_{mission_id[:8]}"
    }
})
resp.raise_for_status()
task = resp.json()
task_id = task["id"]
print(f"   ✓ Task created: {task_id[:12]}...\n")

# 3. Create Job
print("3. Creating job...")
resp = requests.post(f"{BASE_URL}/api/tasks/{task_id}/jobs", json={
    "payload": {
        "kind": "agent_plan",
        "params": {
            "user_request": "Use walk_tree to list all .py files in the core/ directory",
            "iteration": 1
        },
        "task": {
            "kind": "agent_plan",
            "params": {
                "user_prompt": "Use walk_tree to list all .py files in the core/ directory. Return the file list as your final answer."
            }
        }
    }
})
resp.raise_for_status()
job = resp.json()
job_id = job["id"]
print(f"   ✓ Job created: {job_id[:12]}...\n")

# 4. Wait for completion
print("4. Waiting for job completion (max 60s)...")
for i in range(60):
    time.sleep(1)
    resp = requests.get(f"{BASE_URL}/api/jobs/{job_id}")
    job = resp.json()
    status = job.get("status")
    print(f"   [{i+1}s] Status: {status}", end="\r")
    
    if status in ["completed", "failed", "error"]:
        print(f"\n   ✓ Job finished with status: {status}\n")
        break
else:
    print("\n   ✗ Timeout waiting for job\n")

# 5. Check result
print("5. Checking result...")
result = job.get("result") or {}
print(f"   Result keys: {list(result.keys())}")

# Check for LCP envelope
if "type" in result:
    print(f"   ✓ LCP envelope present: type={result['type']}")
    
    if result["type"] == "followup_jobs":
        jobs = result.get("jobs") or []
        print(f"   ✓ Followup jobs created: {len(jobs)}")
        for j in jobs:
            print(f"      - {j.get('kind')}: {j.get('params', {}).get('path', 'N/A')}")
    
    elif result["type"] == "final_answer":
        answer = result.get("answer") or {}
        print(f"   ✓ Final answer received")
        print(f"      {json.dumps(answer, indent=2)[:200]}...")
else:
    print(f"   ✗ No LCP envelope found")
    print(f"   Raw result: {json.dumps(result, indent=2)[:500]}...")

print("\n=== Test Complete ===")
print(f"Mission ID: {mission_id}")
print(f"Job ID: {job_id}")
print(f"Dashboard: http://localhost:3001")
