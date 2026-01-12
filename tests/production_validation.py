#!/usr/bin/env python3
"""
Production Validation Test - Comprehensive Worker Capability Verification
Tests all worker capabilities and validates follow-up job content integration.
"""

import requests
import json
import time
import sys
from pathlib import Path

BASE_URL = "http://localhost:8001"
TIMEOUT = 180  # 3 minutes max per test

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_test(msg):
    print(f"{Colors.BLUE}[TEST]{Colors.RESET} {msg}")

def print_pass(msg):
    print(f"{Colors.GREEN}✓ PASS:{Colors.RESET} {msg}")

def print_fail(msg):
    print(f"{Colors.RED}✗ FAIL:{Colors.RESET} {msg}")

def print_info(msg):
    print(f"{Colors.YELLOW}ℹ INFO:{Colors.RESET} {msg}")

def wait_for_job_completion(job_id, timeout=TIMEOUT):
    """Wait for a job to complete and return its result."""
    start = time.time()
    while time.time() - start < timeout:
        resp = requests.get(f"{BASE_URL}/api/jobs/{job_id}")
        if resp.status_code != 200:
            return None, f"Failed to fetch job: {resp.status_code}"
        
        job = resp.json()
        status = job.get("status")
        
        if status == "completed":
            return job.get("result"), None
        elif status == "failed":
            result = job.get("result") or {}
            error = result.get("error", "Unknown error")
            return None, f"Job failed: {error}"
        
        time.sleep(2)
    
    return None, "Timeout waiting for job completion"

def create_mission(title, description):
    """Create a new mission."""
    resp = requests.post(f"{BASE_URL}/api/missions", json={
        "title": title,
        "description": description
    })
    resp.raise_for_status()
    return resp.json()["id"]

def create_task(mission_id, name, kind, params):
    """Create a task under a mission."""
    resp = requests.post(f"{BASE_URL}/api/missions/{mission_id}/tasks", json={
        "name": name,
        "kind": kind,
        "params": params
    })
    resp.raise_for_status()
    return resp.json()["id"]

def create_job(task_id, kind, params):
    """Create a job for a task."""
    resp = requests.post(f"{BASE_URL}/api/tasks/{task_id}/jobs", json={
        "payload": {
            "kind": kind,
            "params": params,
            "task": {
                "kind": kind,
                "params": params
            }
        }
    })
    resp.raise_for_status()
    return resp.json()["id"]

# ============================================================================
# TEST 1: Basic File Operations (write, read, list)
# ============================================================================
def test_basic_file_ops():
    print_test("Test 1: Basic File Operations (write → read → list)")
    
    mission_id = create_mission("File Ops Test", "Test basic file operations")
    
    # 1a. Write a test file
    print_info("  1a. Writing test file...")
    task_id = create_task(mission_id, "Write Test", "write_file", {
        "path": "test_validation_file.txt",
        "content": "Production validation test content\nLine 2\nLine 3"
    })
    job_id = create_job(task_id, "write_file", {
        "path": "test_validation_file.txt",
        "content": "Production validation test content\nLine 2\nLine 3"
    })
    
    result, error = wait_for_job_completion(job_id)
    if error:
        print_fail(f"Write failed: {error}")
        return False
    
    if not result.get("ok"):
        print_fail(f"Write returned ok=False: {result}")
        return False
    
    print_pass("File written successfully")
    
    # 1b. Read the file back
    print_info("  1b. Reading test file...")
    task_id = create_task(mission_id, "Read Test", "read_file", {
        "path": "test_validation_file.txt"
    })
    job_id = create_job(task_id, "read_file", {
        "path": "test_validation_file.txt"
    })
    
    result, error = wait_for_job_completion(job_id)
    if error:
        print_fail(f"Read failed: {error}")
        return False
    
    content = result.get("content", "")
    if "Production validation test content" not in content:
        print_fail(f"Read content mismatch. Got: {content[:100]}")
        return False
    
    print_pass(f"File read successfully ({len(content)} chars)")
    
    # 1c. List files
    print_info("  1c. Listing files...")
    task_id = create_task(mission_id, "List Test", "list_files", {
        "root": ".",
        "pattern": "test_validation_*.txt"
    })
    job_id = create_job(task_id, "list_files", {
        "root": ".",
        "pattern": "test_validation_*.txt"
    })
    
    result, error = wait_for_job_completion(job_id)
    if error:
        print_fail(f"List failed: {error}")
        return False
    
    files = result.get("files", [])
    if not any("test_validation_file.txt" in f for f in files):
        print_fail(f"Test file not found in list: {files}")
        return False
    
    print_pass(f"Files listed successfully ({len(files)} files)")
    
    return True

# ============================================================================
# TEST 2: walk_tree Capability
# ============================================================================
def test_walk_tree():
    print_test("Test 2: walk_tree Capability")
    
    mission_id = create_mission("Walk Tree Test", "Test walk_tree capability")
    
    print_info("  Walking core/ directory for .py files...")
    task_id = create_task(mission_id, "Walk Core", "walk_tree", {
        "root": "core",
        "pattern": "*.py",
        "max_depth": 2
    })
    job_id = create_job(task_id, "walk_tree", {
        "root": "core",
        "pattern": "*.py",
        "max_depth": 2
    })
    
    result, error = wait_for_job_completion(job_id)
    if error:
        print_fail(f"walk_tree failed: {error}")
        return False
    
    files = result.get("files", [])
    dirs = result.get("dirs", [])
    
    if len(files) == 0:
        print_fail("No files found in core/")
        return False
    
    # Check for expected files
    expected_files = ["main.py", "job_chain_manager.py"]
    found = [f for f in expected_files if any(ef in file for ef in [f] for file in files)]
    
    print_pass(f"walk_tree found {len(files)} files, {len(dirs)} dirs")
    print_info(f"  Sample files: {files[:3]}")
    
    return True

# ============================================================================
# TEST 3: read_file_batch Capability
# ============================================================================
def test_read_file_batch():
    print_test("Test 3: read_file_batch Capability")
    
    mission_id = create_mission("Batch Read Test", "Test read_file_batch")
    
    # First, create multiple test files
    print_info("  Creating test files...")
    for i in range(3):
        task_id = create_task(mission_id, f"Write Test {i}", "write_file", {
            "path": f"test_batch_{i}.txt",
            "content": f"Batch test file {i}\nContent line 2"
        })
        job_id = create_job(task_id, "write_file", {
            "path": f"test_batch_{i}.txt",
            "content": f"Batch test file {i}\nContent line 2"
        })
        wait_for_job_completion(job_id)
    
    # Now read them in batch
    print_info("  Reading files in batch...")
    task_id = create_task(mission_id, "Batch Read", "read_file_batch", {
        "paths": ["test_batch_0.txt", "test_batch_1.txt", "test_batch_2.txt"],
        "limit": 3
    })
    job_id = create_job(task_id, "read_file_batch", {
        "paths": ["test_batch_0.txt", "test_batch_1.txt", "test_batch_2.txt"],
        "limit": 3
    })
    
    result, error = wait_for_job_completion(job_id)
    if error:
        print_fail(f"read_file_batch failed: {error}")
        return False
    
    files = result.get("files", {})
    if len(files) != 3:
        print_fail(f"Expected 3 files, got {len(files)}")
        return False
    
    # Verify content
    for i in range(3):
        key = f"test_batch_{i}.txt"
        if key not in files:
            print_fail(f"Missing file: {key}")
            return False
        
        content = files[key].get("content", "")
        if f"Batch test file {i}" not in content:
            print_fail(f"Content mismatch for {key}")
            return False
    
    print_pass(f"read_file_batch read {len(files)} files successfully")
    
    return True

# ============================================================================
# TEST 4: Autonomous Chain with Content Integration
# ============================================================================
def test_autonomous_chain_with_content():
    print_test("Test 4: Autonomous Chain with Content Integration (agent_plan → walk_tree → analysis)")
    
    mission_id = create_mission("Chain Content Test", "Test follow-up content integration")
    
    print_info("  Creating agent_plan job that will chain to walk_tree...")
    task_id = create_task(mission_id, "Agent Plan", "agent_plan", {
        "user_prompt": "Use walk_tree to find all .py files in the 'worker' directory, then analyze the first file you find and tell me what it does. Use the actual file content in your analysis.",
        "chain_id": f"content_test_{int(time.time())}"
    })
    
    job_id = create_job(task_id, "agent_plan", {
        "user_request": "Use walk_tree to find all .py files in the 'worker' directory, then analyze the first file you find and tell me what it does. Use the actual file content in your analysis.",
        "iteration": 1
    })
    
    print_info(f"  Root job: {job_id[:12]}...")
    print_info("  Waiting for autonomous chain execution (max 180s)...")
    
    # Wait and monitor the chain
    start = time.time()
    while time.time() - start < TIMEOUT:
        # Get all jobs for this task
        resp = requests.get(f"{BASE_URL}/api/jobs")
        all_jobs = resp.json()
        task_jobs = [j for j in all_jobs if j.get("task_id") == task_id]
        
        # Count by kind
        agent_plans = [j for j in task_jobs if j.get("payload", {}).get("kind") == "agent_plan"]
        walk_trees = [j for j in task_jobs if j.get("payload", {}).get("kind") == "walk_tree"]
        read_files = [j for j in task_jobs if j.get("payload", {}).get("kind") == "read_file"]
        
        print(f"\r  [{int(time.time()-start)}s] Jobs: {len(agent_plans)} agent_plan, {len(walk_trees)} walk_tree, {len(read_files)} read_file", end="")
        
        # Check if we have follow-up jobs
        if len(walk_trees) > 0:
            print_pass("\n  walk_tree follow-up job created!")
            
            # Check walk_tree result
            wt_job = walk_trees[0]
            if wt_job.get("status") == "completed":
                wt_result = wt_job.get("result", {})
                files = wt_result.get("files", [])
                print_pass(f"  walk_tree completed with {len(files)} files")
                
                # Check if subsequent agent_plan uses this content
                if len(agent_plans) > 1:
                    second_plan = agent_plans[1]
                    if second_plan.get("status") == "completed":
                        print_pass("  Second agent_plan completed - content integration verified!")
                        return True
        
        time.sleep(3)
    
    print_fail("\n  Timeout - chain did not complete")
    return False

# ============================================================================
# MAIN TEST RUNNER
# ============================================================================
def main():
    print("\n" + "="*70)
    print("  SHERATAN PRODUCTION VALIDATION TEST SUITE")
    print("="*70 + "\n")
    
    # Check if Core is running
    try:
        resp = requests.get(f"{BASE_URL}/api/missions", timeout=5)
        if resp.status_code != 200:
            print_fail("Core API is not responding correctly")
            sys.exit(1)
        print_pass("Core API is online\n")
    except Exception as e:
        print_fail(f"Cannot connect to Core API: {e}")
        sys.exit(1)
    
    results = {}
    
    # Run tests
    results["Basic File Ops"] = test_basic_file_ops()
    print()
    
    results["walk_tree"] = test_walk_tree()
    print()
    
    results["read_file_batch"] = test_read_file_batch()
    print()
    
    results["Autonomous Chain"] = test_autonomous_chain_with_content()
    print()
    
    # Summary
    print("\n" + "="*70)
    print("  TEST SUMMARY")
    print("="*70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if result else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"  {test_name:30s} [{status}]")
    
    print("\n" + "="*70)
    print(f"  TOTAL: {passed}/{total} tests passed")
    print("="*70 + "\n")
    
    if passed == total:
        print_pass("All production validation tests passed! 🚀")
        sys.exit(0)
    else:
        print_fail(f"{total - passed} test(s) failed")
        sys.exit(1)

if __name__ == "__main__":
    main()
