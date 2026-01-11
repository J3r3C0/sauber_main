# Phase 9 E2E Test 3: Loop Guard Test (max_depth)
# Tests: Chain overrides, loop guards, constraint_violation handling

import requests
import json
import time

BASE_URL = "http://localhost:8001"

print("=== Phase 9 Test 3: Loop Guard Test (max_depth) ===\n")

# 1. Create Mission
print("1. Creating mission...")
resp = requests.post(f"{BASE_URL}/api/missions", json={
    "title": "Test Loop Guards",
    "description": "Verify max_depth prevents infinite loops"
})
resp.raise_for_status()
mission = resp.json()
mission_id = mission["id"]
print(f"   ✓ Mission created: {mission_id[:12]}...\n")

# 2. Create agent_plan Task with max_depth override
print("2. Creating agent_plan task with max_depth=3...")
resp = requests.post(f"{BASE_URL}/api/missions/{mission_id}/tasks", json={
    "name": "Infinite exploration attempt",
    "kind": "agent_plan",
    "params": {
        "user_prompt": "Explore the entire codebase recursively. Keep exploring until you are absolutely sure you have seen everything. Use walk_tree and read_file_batch as needed.",
        "chain_id": f"test_guard_{mission_id[:8]}",
        "max_depth": 3  # Override: should stop at depth 3
    }
})
resp.raise_for_status()
task = resp.json()
task_id = task["id"]
print(f"   ✓ Task created: {task_id[:12]}...\n")

# 3. Create Job with overrides in payload params
print("3. Creating job with chain overrides...")
resp = requests.post(f"{BASE_URL}/api/tasks/{task_id}/jobs", json={
    "payload": {
        "kind": "agent_plan",
        "params": {
            "user_request": "Explore the entire codebase recursively. Keep exploring until you are absolutely sure you have seen everything.",
            "max_depth": 3,  # Chain override
            "max_jobs_total": 15,  # Also test this guard
            "iteration": 1
        },
        "task": {
            "kind": "agent_plan",
            "params": {
                "user_prompt": "Explore the entire codebase recursively. Keep exploring until you are absolutely sure you have seen everything. Use walk_tree and read_file_batch as needed."
            }
        }
    }
})
resp.raise_for_status()
job = resp.json()
job_id = job["id"]
print(f"   ✓ Job created: {job_id[:12]}...\n")

# 4. Monitor chain execution
print("4. Monitoring chain execution (max 120s)...")
max_depth_reached = False
constraint_violation_found = False

for i in range(120):
    time.sleep(1)
    
    # Get all jobs for this task
    resp = requests.get(f"{BASE_URL}/api/jobs")
    all_jobs = resp.json()
    task_jobs = [j for j in all_jobs if j.get("task_id") == task_id]
    
    # Count agent_plan jobs and check depth
    agent_plans = [j for j in task_jobs if j.get("payload", {}).get("kind") == "agent_plan"]
    completed_plans = [j for j in agent_plans if j.get("status") == "completed"]
    
    # Check for max_depth in chain hints
    max_depth_seen = 0
    for j in task_jobs:
        hint = j.get("payload", {}).get("_chain_hint") or {}
        depth = hint.get("depth", 0)
        if depth > max_depth_seen:
            max_depth_seen = depth
    
    print(f"   [{i+1}s] Jobs: {len(agent_plans)} agent_plan, max_depth_seen: {max_depth_seen}", end="\r")
    
    # Check if chain stopped due to max_depth
    if len(completed_plans) > 0:
        last_plan = completed_plans[-1]
        result = last_plan.get("result") or {}
        
        # Check for constraint_violation in payload
        payload = last_plan.get("payload") or {}
        params = payload.get("params") or {}
        llm_input = params.get("input") or {}
        constraint_violation = llm_input.get("constraint_violation")
        
        if constraint_violation:
            constraint_violation_found = True
            print(f"\n   ✓ Constraint violation detected: {constraint_violation}\n")
        
        if result.get("type") == "final_answer":
            print(f"\n   ✓ Chain completed with final answer\n")
            if max_depth_seen >= 3:
                max_depth_reached = True
            break
else:
    print("\n   ⚠ Timeout - chain may still be running\n")

# 5. Verify guards worked
print("5. Verifying loop guards...")
resp = requests.get(f"{BASE_URL}/api/jobs")
all_jobs = resp.json()
task_jobs = [j for j in all_jobs if j.get("task_id") == task_id]

# Check chain file
chain_id = f"test_guard_{mission_id[:8]}"
try:
    import os
    from pathlib import Path
    chain_file = Path("c:/sauber_main/data/chains") / f"{chain_id}.json"
    if chain_file.exists():
        with open(chain_file, "r") as f:
            chain_data = json.load(f)
        
        print(f"   Chain state:")
        print(f"      max_depth (config): {chain_data.get('max_depth')}")
        print(f"      depth (reached): {chain_data.get('depth')}")
        print(f"      max_jobs_total (config): {chain_data.get('max_jobs_total')}")
        print(f"      jobs_total (created): {chain_data.get('jobs_total')}")
        print(f"      status: {chain_data.get('status')}")
        print(f"      failed_reason: {chain_data.get('failed_reason')}")
        
        # Verify overrides were applied
        if chain_data.get('max_depth') == 3:
            print(f"\n   ✓ max_depth override applied correctly")
        else:
            print(f"\n   ✗ max_depth override NOT applied (expected 3, got {chain_data.get('max_depth')})")
        
        if chain_data.get('max_jobs_total') == 15:
            print(f"   ✓ max_jobs_total override applied correctly")
        else:
            print(f"   ✗ max_jobs_total override NOT applied (expected 15, got {chain_data.get('max_jobs_total')})")
        
        # Verify depth guard worked
        if chain_data.get('depth') <= 3:
            print(f"   ✓ Depth guard enforced (stopped at depth {chain_data.get('depth')})")
        else:
            print(f"   ✗ Depth guard FAILED (reached depth {chain_data.get('depth')})")
    else:
        print(f"   ⚠ Chain file not found: {chain_file}")
except Exception as e:
    print(f"   ⚠ Could not read chain file: {e}")

print(f"\n   Total jobs created: {len(task_jobs)}")
print(f"   Constraint violation found: {constraint_violation_found}")
print(f"   Max depth reached: {max_depth_reached}")

print("\n=== Test Complete ===")
print(f"Mission ID: {mission_id}")
print(f"Root Job ID: {job_id}")
print(f"Chain ID: {chain_id}")
print(f"Dashboard: http://localhost:3001")
