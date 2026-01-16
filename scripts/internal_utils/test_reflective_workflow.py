"""Test REFLECTIVE state workflow and anomaly auto-trigger."""
import sys
from core.state_machine import SystemStateMachine, SystemState
from core.performance_baseline import PerformanceBaselineTracker
from core.self_diagnostics import SelfDiagnosticEngine, DiagnosticConfig
from core.anomaly_detector import AnomalyDetector

# Initialize components
sm = SystemStateMachine()
sm.load_or_init()
baseline = PerformanceBaselineTracker()
anomaly = AnomalyDetector()
config = DiagnosticConfig(reflective_enabled=True)
diagnostic = SelfDiagnosticEngine(
    state_machine=sm,
    baseline_tracker=baseline,
    anomaly_detector=anomaly,
    config=config
)

# Wire components
anomaly.set_reflective_trigger(diagnostic.enter_reflective_mode)
print("✅ Components wired")

# Test 1: Manual REFLECTIVE trigger
print("\n=== Test 1: Manual REFLECTIVE Trigger ===")
print(f"Current state: {sm.snapshot().state}")

try:
    diagnostic.enter_reflective_mode(
        reason="Manual test trigger",
        trigger_data={"test": True}
    )
    print(f"✅ REFLECTIVE workflow completed successfully")
except Exception as e:
    print(f"❌ REFLECTIVE mode failed: {e}")
    sys.exit(1)

final_state = sm.snapshot().state
print(f"Final state: {final_state}")

# Verify state transitioned correctly
if final_state not in [SystemState.OPERATIONAL.value, SystemState.DEGRADED.value, SystemState.RECOVERY.value]:
    print(f"❌ Unexpected final state: {final_state}")
    sys.exit(1)

# Test 2: Anomaly auto-trigger
print("\n=== Test 2: Anomaly Auto-Trigger ===")

# Reset to OPERATIONAL
if sm.snapshot().state != SystemState.OPERATIONAL.value:
    sm.transition(SystemState.OPERATIONAL, reason="Reset for test")

# Inject critical anomalies
anomalies = [
    {"severity": "error", "message": "Test critical 1"},
    {"severity": "error", "message": "Test critical 2"},
    {"severity": "error", "message": "Test critical 3"},
]

print(f"Injecting {len(anomalies)} critical anomalies...")
triggered = anomaly.check_trigger_threshold(anomalies)

if not triggered:
    print("❌ Anomaly threshold not triggered")
    sys.exit(1)

print(f"✅ REFLECTIVE triggered: {triggered}")
print(f"Final state: {sm.snapshot().state}")

print("\n✅ All REFLECTIVE workflow tests passed!")
