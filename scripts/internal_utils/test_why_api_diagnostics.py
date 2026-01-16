"""Test WHY-API diagnostic extensions."""
import requests
import sys

BASE_URL = "http://localhost:8001/api/why"

def test_endpoint(name, url):
    """Test an endpoint and print results."""
    print(f"\n=== Testing {name} ===")
    try:
        response = requests.get(url, timeout=5)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: {data.get('ok', False)}")
            
            # Print relevant data
            if 'baselines' in data:
                metrics = data.get('baselines', {}).get('metrics', [])
                print(f"   Metrics tracked: {len(metrics)}")
            elif 'anomalies' in data:
                count = data.get('count', 0)
                print(f"   Anomalies found: {count}")
            elif 'latest_report' in data:
                health = data.get('latest_report', {}).get('health_score', 'N/A')
                print(f"   Health score: {health}")
            elif 'transitions' in data:
                count = data.get('count', 0)
                print(f"   Transitions: {count}")
                analysis = data.get('analysis', {})
                if analysis.get('flapping_detected'):
                    print(f"   ⚠️  Flapping detected: {analysis['flapping_detected']}")
            
            return True
        else:
            print(f"❌ Failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

# Test all endpoints
print("Testing WHY-API Diagnostic Extensions...")
print("=" * 50)

tests = [
    ("Baselines", f"{BASE_URL}/baselines"),
    ("Baselines (filtered)", f"{BASE_URL}/baselines?metric=state_transition_rate"),
    ("Anomalies", f"{BASE_URL}/anomalies?window=1h"),
    ("Diagnostics", f"{BASE_URL}/diagnostics"),
    ("State Transitions", f"{BASE_URL}/state-transitions?limit=20"),
]

results = []
for name, url in tests:
    results.append(test_endpoint(name, url))

# Summary
print("\n" + "=" * 50)
print(f"Results: {sum(results)}/{len(results)} tests passed")

if all(results):
    print("✅ All WHY-API diagnostic endpoints working!")
    sys.exit(0)
else:
    print("❌ Some tests failed")
    sys.exit(1)
