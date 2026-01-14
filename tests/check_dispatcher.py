"""
Quick diagnostic: Check if Dispatcher is running
"""
import requests
import time

def check_dispatcher():
    try:
        # Check system health
        resp = requests.get("http://localhost:8000/api/health")
        health = resp.json()
        
        print("=== SYSTEM HEALTH ===")
        print(f"Overall: {health.get('overall')}")
        print(f"Services: {health.get('services')}")
        
        # Check if dispatcher is mentioned
        if 'dispatcher' in str(health):
            print("\n✅ Dispatcher mentioned in health check")
        else:
            print("\n❌ Dispatcher NOT mentioned in health check")
        
        # Check pending jobs
        resp = requests.get("http://localhost:8000/api/jobs")
        jobs = resp.json()
        
        pending = [j for j in jobs if j['status'] == 'pending']
        working = [j for j in jobs if j['status'] == 'working']
        
        print(f"\n=== JOB STATUS ===")
        print(f"Pending: {len(pending)}")
        print(f"Working: {len(working)}")
        
        if pending:
            print("\nPending jobs:")
            for j in pending[:5]:
                print(f"  {j['id'][:8]} | created: {j['created_at']}")
        
        return len(pending) > 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    has_pending = check_dispatcher()
    
    if has_pending:
        print("\n⚠️ DISPATCHER ISSUE: Jobs stuck in pending")
        print("Expected: Dispatcher should move pending → working")
    else:
        print("\n✅ No pending jobs (Dispatcher working or no jobs)")
