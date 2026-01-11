import json
from pathlib import Path

def print_status():
    f = Path("data/jobs.jsonl")
    if not f.exists():
        print("File not found")
        return
    with open(f, "r", encoding="utf-8") as file:
        lines = file.readlines()
    
    print(f"{'ID':8} | {'KIND':15} | {'STATUS':10} | {'PAYLOAD_KEYS'}")
    print("-" * 50)
    for l in lines[-10:]:
        try:
            j = json.loads(l)
            payload = j.get("payload", {})
            kind = payload.get("task", {}).get("kind") if isinstance(payload, dict) else None
            if not kind and isinstance(payload, dict):
                kind = payload.get("kind")
            if not kind: kind = "unknown"
            
            p_keys = list(payload.keys()) if isinstance(payload, dict) else "N/A"
            print(f"{j['id'][:8]} | {kind:15} | {j['status']:10} | {p_keys}")
        except Exception as e:
            print(f"Error parsing line: {e}")

if __name__ == "__main__":
    print_status()
