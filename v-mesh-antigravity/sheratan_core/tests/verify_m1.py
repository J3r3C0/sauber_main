import requests
import sys

BASE_URL = "http://localhost:8001/v1"

def test_m1():
    print("--- Milestone 1: Basics ---")
    
    try:
        # 1. POST Mission
        m_res = requests.post(f"{BASE_URL}/missions", json={"title": "M1 Mission", "description": "Test"})
        m_res.raise_for_status()
        m_id = m_res.json()["id"]
        print(f"Created Mission: {m_id}")

        # 2. POST Job
        j_payload = {"mission_id": m_id, "envelope": {"task": "test"}}
        j_res = requests.post(f"{BASE_URL}/jobs", json=j_payload)
        j_res.raise_for_status()
        j_id = j_res.json()["id"]
        print(f"Created Job: {j_id}")

        # 3. GET next job
        next_res = requests.get(f"{BASE_URL}/jobs/next")
        next_job = next_res.json()
        if not next_job or next_job["id"] != j_id:
            print(f"Error: Expected job {j_id}, got {next_job}")
            sys.exit(1)
        print(f"Leased Job: {next_job['id']}")

        # 4. POST Result
        r_res = requests.post(f"{BASE_URL}/results", json={"job_id": j_id, "result": {"ok": True}})
        r_res.raise_for_status()
        print(f"Posted Result: {r_res.json()}")

        # 5. GET Job state
        state_res = requests.get(f"{BASE_URL}/jobs/{j_id}")
        state_res.raise_for_status()
        state = state_res.json()
        if state["state"] != "completed":
            print(f"Error: Expected completed, got {state['state']}")
            sys.exit(1)
        
        print("Milestone 1: VERIFIED ✅")

    except Exception as e:
        print(f"M1 Failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_m1()
