import json
from pathlib import Path

def check():
    jobs_file = Path("data/jobs.jsonl")
    if not jobs_file.exists():
        print("Jobs file not found.")
        return

    with open(jobs_file, "r", encoding="utf-8") as f:
        lines = f.readlines()
    
    jobs = [json.loads(l) for l in lines]
    
    # Find the latest agent_plan
    for i in range(len(jobs)-1, -1, -1):
        job = jobs[i]
        payload = job.get("payload", {})
        
        # Is it an agent_plan?
        if payload.get("task", {}).get("kind") == "agent_plan":
            last_result = payload.get("last_result", {})
            content = last_result.get("content", "")
            is_truncated = last_result.get("_truncated", False)
            path = last_result.get("path") or last_result.get("rel_path")
            
            print(f"\n--- VERIFICATION REPORT (Job: {job['id'][:8]}) ---")
            print(f"📄 Target Path: {path}")
            print(f"📊 Content Size: {len(content)} chars")
            print(f"✂️ Core Truncated Flag: {is_truncated}")
            
            if len(content) > 1500:
                print("✅ [OK] Content is > 1KB (Truncation Bypass working!)")
            else:
                print("⚠️ [WARN] Content is small (< 1KB). This might be a small file or truncation.")

            if is_truncated:
                 print("❌ [FAIL] Core marked this as truncated!")
            else:
                 print("✅ [OK] Core 'full_content' respect is ACTIVE.")
            
            # Check for path hallucinations
            if path and ("C:/workspace" in path or "C:\\workspace" in path):
                print("❌ [FAIL] Path still contains hallucinated root!")
            else:
                print("✅ [OK] Path Sanitization is ACTIVE.")
            return

    print("❓ No agent_plan found in history. Start a mission first!")

if __name__ == "__main__":
    check()
