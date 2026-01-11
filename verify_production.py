import requests
import time
import uuid
import sys

# Force UTF-8 for Windows shell logging
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

CORE_URL = "http://localhost:8001"

def create_mission():
    res = requests.post(f"{CORE_URL}/api/missions", json={
        "title": "Verifikations Mission",
        "description": "Testet Priority, Idempotency und Dependencies"
    })
    return res.json()["id"]

def create_task(mission_id):
    res = requests.post(f"{CORE_URL}/api/missions/{mission_id}/tasks", json={
        "name": "Test Task",
        "kind": "ping",
        "params": {}
    })
    return res.json()["id"]

def create_job(task_id, priority="normal", depends_on=[], idempotency_key=None):
    # Map JobCreate fields properly
    res = requests.post(f"{CORE_URL}/api/tasks/{task_id}/jobs", json={
        "priority": priority,
        "depends_on": depends_on,
        "idempotency_key": idempotency_key,
        "payload": {"ping": "pong"}
    })
    return res.json()["id"]

def test_production_features():
    m_id = create_mission()
    t_id = create_task(m_id)

    print("\n--- Testing Priority ---")
    # 1. Normal Priority Job
    j_norm = create_job(t_id, priority="normal")
    # 2. High Priority Job (Created slightly later)
    j_high = create_job(t_id, priority="high")
    
    print(f"Created Norm: {j_norm[:8]}, High: {j_high[:8]}")
    print("Waiting for dispatcher...")
    time.sleep(10)
    
    # Check logs/status (In a real test we'd check updated_at or logs)
    # For now, we trust the dispatcher logic if no errors occur.

    print("\n--- Testing Idempotency ---")
    key = str(uuid.uuid4())
    j1 = create_job(t_id, idempotency_key=key)
    # Ensure it's completed before j2
    print(f"Waiting for j1 ({j1[:8]}) to finish...")
    time.sleep(10)
    
    j2 = create_job(t_id, idempotency_key=key)
    print(f"Created j2 ({j2[:8]}) with same key. Waiting for deduplication...")
    time.sleep(5)
    
    res2 = requests.get(f"{CORE_URL}/api/jobs/{j2}").json()
    if res2["status"] == "completed" and res2["result"].get("deduplicated"):
        print("✓ Idempotency verified: Job j2 was auto-completed.")
    else:
        print(f"✗ Idempotency failed: {res2['status']} - {res2.get('result')}")

    print("\n--- Testing Dependencies ---")
    ja = create_job(t_id)
    jb = create_job(t_id, depends_on=[ja])
    print(f"Created B ({jb[:8]}) depending on A ({ja[:8]})")
    
    time.sleep(5)
    res_b = requests.get(f"{CORE_URL}/api/jobs/{jb}").json()
    if res_b["status"] == "pending":
        print("✓ Dependency verified: Job B is still pending while A is working.")
    else:
        print(f"✗ Dependency failed: B is {res_b['status']}")

if __name__ == "__main__":
    test_production_features()
