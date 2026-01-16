"""Test WHY-API diagnostic extensions (direct function calls)."""
import sys

print("Testing WHY-API Diagnostic Extensions (Direct)...")
print("=" * 50)

# Test 1: Baselines
print("\n=== Test 1: Baselines ===")
try:
    from core.why_api import why_baselines
    result = why_baselines()
    print(f"✅ Baselines endpoint works")
    print(f"   Metrics: {len(result.get('baselines', {}).get('metrics', []))}")
except Exception as e:
    print(f"❌ Baselines failed: {e}")
    sys.exit(1)

# Test 2: Anomalies
print("\n=== Test 2: Anomalies ===")
try:
    from core.why_api import why_anomalies
    result = why_anomalies()
    print(f"✅ Anomalies endpoint works")
    print(f"   Count: {result.get('count', 0)}")
except Exception as e:
    print(f"❌ Anomalies failed: {e}")
    sys.exit(1)

# Test 3: Diagnostics
print("\n=== Test 3: Diagnostics ===")
try:
    from core.why_api import why_diagnostics
    result = why_diagnostics()
    if result.get('ok'):
        print(f"✅ Diagnostics endpoint works")
        health = result.get('latest_report', {}).get('health_score', 'N/A')
        print(f"   Health score: {health}")
    else:
        print(f"⚠️  No diagnostic reports yet (expected on first run)")
except Exception as e:
    print(f"❌ Diagnostics failed: {e}")
    sys.exit(1)

# Test 4: State Transitions
print("\n=== Test 4: State Transitions ===")
try:
    from core.why_api import why_state_transitions
    result = why_state_transitions()
    print(f"✅ State transitions endpoint works")
    print(f"   Transitions: {result.get('count', 0)}")
    analysis = result.get('analysis', {})
    if analysis.get('flapping_detected'):
        print(f"   ⚠️  Flapping: {analysis['flapping_detected']}")
    print(f"   Current state: {analysis.get('current_state', 'N/A')}")
except Exception as e:
    print(f"❌ State transitions failed: {e}")
    sys.exit(1)

print("\n" + "=" * 50)
print("✅ All WHY-API diagnostic endpoints working!")
