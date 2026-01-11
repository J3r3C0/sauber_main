import requests
import sys
import json
import os
from datetime import datetime

# --- CONFIGURATION ---
# Replace with your PC's local IP
DEFAULT_CORE_URL = "http://192.168.1.206:8001" 

class SheratanRemote:
    def __init__(self, base_url):
        self.base_url = base_url

    def get_status(self):
        try:
            res = requests.get(f"{self.base_url}/api/status", timeout=2)
            if res.status_code == 200:
                data = res.json()
                print(f"\n[Sheratan] 🟢 Online")
                print(f"Missions: {data.get('missions', 0)}")
                return True
        except:
            print(f"\n[Sheratan] 🔴 Offline (URL: {self.base_url})")
            return False

    def list_jobs(self):
        try:
            res = requests.get(f"{self.base_url}/api/jobs", timeout=2)
            jobs = res.json()
            print("\n--- Current Jobs ---")
            for j in jobs[-5:]: # Last 5
                status_icon = "⏳" if j['status'] == 'pending' else "⚙️" if j['status'] == 'working' else "✅"
                print(f"{status_icon} {j['id'][:8]} | {j['status']} | P: {j.get('priority', 'normal')}")
        except Exception as e:
            print(f"Error: {e}")

    def quick_mission(self, prompt):
        try:
            # Using the Core's standard mission template endpoint
            res = requests.post(f"{self.base_url}/api/missions/standard-code-analysis", timeout=5)
            if res.status_code == 200:
                data = res.json()
                print(f"\n🚀 Mission Launched: {data['mission']['id'][:8]}")
                print(f"Job ID: {data['job']['id'][:8]}")
            else:
                print(f"Failed: {res.text}")
        except Exception as e:
            print(f"Error: {e}")

def main():
    core_url = os.getenv("CORE_URL", DEFAULT_CORE_URL)
    remote = SheratanRemote(core_url)

    if len(sys.argv) < 2:
        print("Sheratan Mobile Hub v1.0")
        print("Usage: python mobile_cli.py [status|jobs|launch]")
        return

    cmd = sys.argv[1]
    if cmd == "status":
        remote.get_status()
    elif cmd == "jobs":
        remote.list_jobs()
    elif cmd == "launch":
        remote.quick_mission("Mobile Request")
    else:
        print("Unknown command.")

if __name__ == "__main__":
    main()
