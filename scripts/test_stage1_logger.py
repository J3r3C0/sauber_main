"""
Stage 1 Test: DecisionTrace Logger with Breach Separation

Tests:
1. Valid event (Golden Sample) → main log
2. Invalid event → breach log
3. Main log contains only valid events
"""

import json
import sys
from pathlib import Path

# Add parent dir to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.decision_trace import trace_logger

def test_valid_event():
    """Test that Golden Sample writes to main log"""
    print("\n[TEST 1] Valid event (Golden Sample)...")
    
    golden = json.load(open("schemas/examples/decision_trace_v1.golden.json"))
    
    try:
        node_id = trace_logger.log_node(
            trace_id=golden["trace_id"],
            intent=golden["intent"],
            build_id=golden["build_id"],
            state=golden["state"],
            action=golden["action"],
            result=golden["result"],
            job_id=golden.get("job_id"),
            parent_node_id=golden.get("parent_node_id"),
            depth=golden["depth"]
        )
        print(f"✓ Valid event logged with node_id: {node_id}")
        return True
    except Exception as e:
        print(f"✗ FAILED: {e}")
        return False

def test_invalid_event():
    """Test that invalid event writes to breach log"""
    print("\n[TEST 2] Invalid event (missing required fields)...")
    
    try:
        # This should fail - missing required fields
        trace_logger.log_node(
            trace_id="test",
            intent="test_intent",
            build_id="test_build",
            state={},  # Invalid - missing required fields
            action={},  # Invalid - missing required fields
            result={}   # Invalid - missing required fields
        )
        print("✗ FAILED: Should have raised ValueError")
        return False
    except ValueError as e:
        print(f"✓ Correctly rejected invalid event: {e}")
        return True

def verify_logs():
    """Verify log separation"""
    print("\n[TEST 3] Verify log separation...")
    
    main_log = Path("logs/decision_trace.jsonl")
    breach_log = Path("logs/decision_trace_breaches.jsonl")
    
    if not main_log.exists():
        print("✗ Main log doesn't exist")
        return False
    
    if not breach_log.exists():
        print("✗ Breach log doesn't exist")
        return False
    
    # Check main log contains only valid events
    with open(main_log) as f:
        lines = f.readlines()
        print(f"  Main log: {len(lines)} events")
        
        for i, line in enumerate(lines):
            try:
                event = json.loads(line)
                assert event["schema_version"] == "decision_trace_v1"
            except Exception as e:
                print(f"✗ Invalid event in main log at line {i+1}: {e}")
                return False
    
    # Check breach log
    with open(breach_log) as f:
        breaches = f.readlines()
        print(f"  Breach log: {len(breaches)} breaches")
    
    print("✓ Log separation verified")
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("Stage 1: DecisionTrace Logger Test")
    print("=" * 60)
    
    results = [
        test_valid_event(),
        test_invalid_event(),
        verify_logs()
    ]
    
    print("\n" + "=" * 60)
    if all(results):
        print("✓ ALL TESTS PASSED")
        print("=" * 60)
        sys.exit(0)
    else:
        print("✗ SOME TESTS FAILED")
        print("=" * 60)
        sys.exit(1)
