# Phase 9 E2E Test 2: Two-Step Chain (walk_tree + read_file_batch)
# Tests: Multi-step chaining, read_file_batch capability, budget tracking

import requests
import json
import time

BASE_URL = "http://localhost:8001"

print("=== Phase 9 Test 2: Two-Step Chain (walk_tree + read_file_batch) ===\n")

# 1. Create Mission
print("1. Creating mission...")
resp = requests.post(f"{BASE_URL}/api/missions", json={
    "title": "Test Read Batch",
    "description": "Read multiple files in batch and summarize"
})
resp.raise_for_status()
mission = resp.json()
mission_id = mission["id"]
print(f"   ✓ Mission created: {mission_id[:12]}...\n")

# 2. Create agent_plan Task
print("2. Creating agent_plan task...")
resp = requests.post(f"{BASE_URL}/api/missions/{mission_id}/tasks", json={
    "name": "Read core files",
    "kind": "agent_plan",
    "params": {
        "user_prompt": "First use walk_tree to find .py files in core/, then use read_file_batch to read the first 3 files and provide a brief summary of what each file does.",
        "chain_id": f"test_batch_{mission_id[:8]}"
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
            "user_request": "First use walk_tree to find .py files in core/, then use read_file_batch to read the first 3 files and summarize them",
            "iteration": 1
        },
        "task": {
            "kind": "agent_plan",
            "params": {
                "user_prompt": "First use walk_tree to find .py files in core/, then use read_file_batch to read the first 3 files and provide a brief summary of what each file does."
            }
        }
    }
})
resp.raise_for_status()
job = resp.json()
job_id = job["id"]
print(f"   ✓ Job created: {job_id[:12]}...\n")

# 4. Wait for completion and monitor chain
print("4. Monitoring chain execution (max 120s)...")
chain_jobs = []
for i in range(120):
    time.sleep(1)
    
    # Get all jobs for this task
    resp = requests.get(f"{BASE_URL}/api/jobs")
    all_jobs = resp.json()
    task_jobs = [j for j in all_jobs if j.get("task_id") == task_id]
    
    # Count by kind
    agent_plans = [j for j in task_jobs if j.get("payload", {}).get("kind") == "agent_plan"]
    walk_trees = [j for j in task_jobs if j.get("payload", {}).get("kind") == "walk_tree"]
    read_batches = [j for j in task_jobs if j.get("payload", {}).get("kind") == "read_file_batch"]
    
    print(f"   [{i+1}s] Jobs: {len(agent_plans)} agent_plan, {len(walk_trees)} walk_tree, {len(read_batches)} read_batch", end="\r")
    
    # Check if chain is complete
    completed_agent_plans = [j for j in agent_plans if j.get("status") == "completed"]
    if len(completed_agent_plans) >= 2:  # Initial + at least one follow-up
        last_job = completed_agent_plans[-1]
        result = last_job.get("result") or {}
        if result.get("type") == "final_answer":
            print(f"\n   ✓ Chain completed with final answer\n")
            break
else:
    print("\n   ⚠ Timeout - chain may still be running\n")

# 5. Analyze chain execution
print("5. Analyzing chain execution...")
resp = requests.get(f"{BASE_URL}/api/jobs")
all_jobs = resp.json()
task_jobs = [j for j in all_jobs if j.get("task_id") == task_id]

agent_plans = [j for j in task_jobs if j.get("payload", {}).get("kind") == "agent_plan"]
walk_trees = [j for j in task_jobs if j.get("payload", {}).get("kind") == "walk_tree"]
read_batches = [j for j in task_jobs if j.get("payload", {}).get("kind") == "read_file_batch"]

print(f"   Total jobs created: {len(task_jobs)}")
print(f"   - agent_plan: {len(agent_plans)}")
print(f"   - walk_tree: {len(walk_trees)}")
print(f"   - read_file_batch: {len(read_batches)}")

# Check walk_tree result
if walk_trees:
    wt = walk_trees[0]
    wt_result = wt.get("result") or {}
    if wt_result.get("ok"):
        files = wt_result.get("files") or []
        truncated = wt_result.get("truncated")
        print(f"\n   walk_tree result:")
        print(f"      Files found: {len(files)}")
        print(f"      Truncated: {truncated}")
        print(f"      First 3: {files[:3]}")

# Check read_file_batch result
if read_batches:
    rb = read_batches[0]
    rb_result = rb.get("result") or {}
    if rb_result.get("ok"):
        files_read = rb_result.get("files") or {}
        any_truncated = rb_result.get("truncated")
        limits = rb_result.get("limits") or {}
        print(f"\n   read_file_batch result:")
        print(f"      Files read: {len(files_read)}")
        print(f"      Any truncated: {any_truncated}")
        print(f"      Limits: {limits}")
        for fp, data in list(files_read.items())[:2]:
            trunc = data.get("truncated", False)
            content_len = len(data.get("content", ""))
            print(f"      - {fp}: {content_len} chars, truncated={trunc}")

# Check final answer
if agent_plans:
    last_agent = agent_plans[-1]
    result = last_agent.get("result") or {}
    if result.get("type") == "final_answer":
        answer = result.get("answer") or {}
        print(f"\n   ✓ Final answer received:")
        print(f"      {json.dumps(answer, indent=2)[:300]}...")

print("\n=== Test Complete ===")
print(f"Mission ID: {mission_id}")
print(f"Root Job ID: {job_id}")
print(f"Dashboard: http://localhost:3001")
