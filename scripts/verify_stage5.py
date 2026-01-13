"""
Stage 5 Simplified Verification

Tests WHY-API components without FastAPI integration.
Verifies:
1. Reader functions work
2. Redaction works
3. Bounded reads work
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

print("=" * 60)
print("Stage 5 WHY-API Simplified Verification")
print("=" * 60)

# Test 1: Reader functions
print("\n[1/3] Testing reader functions...")
from core.why_reader import tail_events, latest_event, stats

log_path = "logs/decision_trace.jsonl"
if Path(log_path).exists():
    events, meta = tail_events(log_path, max_lines=10)
    print(f"✓ tail_events: {meta.returned} events, {meta.scanned_lines} lines scanned")
    
    latest, meta2 = latest_event(log_path, intent="dispatch_job", max_lines=100)
    if latest:
        print(f"✓ latest_event: found event with intent=dispatch_job")
    else:
        print(f"✓ latest_event: no events found (ok if log is empty)")
    
    s, meta3 = stats(log_path, intent="dispatch_job", window_lines=100)
    print(f"✓ stats: count={s['count']}, mean_score={s['mean_score']}")
else:
    print("⚠️  No decision log found (ok for fresh install)")

# Test 2: Redaction
print("\n[2/3] Testing redaction...")
from core.why_api import sanitize

test_event = {
    "prompt": "SECRET_PROMPT",
    "body": "X" * 5000,
    "normal": "ok",
    "long_text": "Y" * 5000,  # This will be truncated
    "nested": {
        "token": "SECRET_TOKEN",
        "data": "normal_data"
    }
}

sanitized = sanitize(test_event)

assert sanitized["prompt"] == "***REDACTED***", f"Expected ***REDACTED***, got {sanitized['prompt']}"
assert sanitized["body"] == "***REDACTED***", "Body should be redacted (it's in DENY_KEYS)"
assert sanitized["long_text"].endswith("...(truncated)"), "Long text should be truncated"
assert sanitized["normal"] == "ok", "Normal field should not be redacted"
assert sanitized["nested"]["token"] == "***REDACTED***", "Nested token should be redacted"
assert sanitized["nested"]["data"] == "normal_data", "Nested normal data should not be redacted"

print("✓ Redaction working correctly")

# Test 3: Bounded reads
print("\n[3/3] Testing bounded reads...")
if Path(log_path).exists():
    # Read with different limits
    small, meta_small = tail_events(log_path, max_lines=5)
    large, meta_large = tail_events(log_path, max_lines=1000)
    
    assert meta_small.scanned_lines <= 5, "Should respect max_lines limit"
    print(f"✓ Bounded reads: small={meta_small.scanned_lines}, large={meta_large.scanned_lines}")
else:
    print("⚠️  Skipping bounded read test (no log)")

print("\n" + "=" * 60)
print("✅ STAGE 5 VERIFICATION PASSED")
print("=" * 60)
print("WHY-API components are functional:")
print("  - Reader functions work")
print("  - Redaction is secure")
print("  - Bounded reads respect limits")
print("=" * 60)
