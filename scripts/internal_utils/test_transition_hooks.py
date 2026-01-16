"""Test state transition hooks integration."""
from core.state_machine import SystemStateMachine, SystemState
from core.performance_baseline import PerformanceBaselineTracker

# Initialize components
sm = SystemStateMachine()
sm.load_or_init()
baseline = PerformanceBaselineTracker()

# Register hook
sm.register_hook(baseline.on_state_transition)

print(f"Initial state: {sm.snapshot().state}")

# Test transition
print("Testing transition PAUSED -> OPERATIONAL...")
sm.transition(SystemState.OPERATIONAL, reason="test hook integration")

# Check baseline was updated
baselines = baseline.get_all_baselines(recompute=True)
print(f"\nBaselines after transition:")
print(f"  state_transition_rate: {baselines['baselines'].get('state_transition_rate', {})}")
print(f"  time_in_paused: {baselines['baselines'].get('time_in_paused', {})}")

# Test another transition
print("\nTesting transition OPERATIONAL -> DEGRADED...")
sm.transition(SystemState.DEGRADED, reason="test degraded tracking")

baselines = baseline.get_all_baselines(recompute=True)
print(f"\nBaselines after second transition:")
print(f"  degraded_state_entered: {baselines['baselines'].get('degraded_state_entered', {})}")

print("\n✅ Hook integration test complete!")
