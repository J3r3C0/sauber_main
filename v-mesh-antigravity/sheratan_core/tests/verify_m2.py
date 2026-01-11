import requests
import json
import sys
import os

BASE_URL = "http://localhost:8001/v1"
FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")

def test_m2():
    print("--- Milestone 2: Leasing & Worker Pull ---")
    
    try:
        # Load fixture
        with open(os.path.join(FIXTURES_DIR, "job_03_worker.json"), "r") as f:
            job_spec = json.load(f)

        # 1. POST Job
        j_res = requests.post(f"{BASE_URL}/jobs", json={"envelope": job_spec})
        j_res.raise_for_status()
        j_id = j_res.json()["id"]
        print(f"Created Job: {j_id}")

        # 2. Lease via next
        lease_res = requests.get(f"{BASE_URL}/jobs/next?consumer=test-worker&instance_id=node-1")
        lease_res.raise_for_status()
        leased = lease_res.json()
        
        if not leased or leased["id"] != j_id:
            print(f"Error: Expected to lease {j_id}, got {leased}")
            sys.exit(1)
            
        print(f"Leased Job {j_id} - state: {leased['state']}, by: {leased['lease']['leased_by']}")

        # 3. Verify it's NOT offered again
        second_lease = requests.get(f"{BASE_URL}/jobs/next")
        if second_lease.json() is not None:
             # Check if it returned the SAME job
             if second_lease.json().get("id") == j_id:
                print("Error: Job was offered again after leasing!")
                sys.exit(1)
        
        print("Verified: Job is locked (not offered again)")

        # 4. Trigger Reaper (Mock)
        reap_res = requests.post(f"{BASE_URL}/maintenance/leases/reap")
        print(f"Reaper triggered: {reap_res.json()}")

        # 5. POST Result
        r_res = requests.post(f"{BASE_URL}/results", json={"job_id": j_id, "result": {"data": "done"}})
        r_res.raise_for_status()
        print("Result submitted")

        # 6. Final State Check
        state_res = requests.get(f"{BASE_URL}/jobs/{j_id}")
        state = state_res.json()
        if state["state"] != "completed":
            print(f"Error: Expected completed, got {state['state']}")
            sys.exit(1)

        print("Milestone 2: VERIFIED ✅")

    except Exception as e:
        print(f"M2 Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_m2()
