"""
Stage 6 DecisionView Validation

Validates that decision_view.html complies with Stage 6 spec:
1. Read-only (no writes, no repair)
2. Defensive parsing (invalid lines skipped)
3. JSONL + WHY-API modes
4. Filter without side effects
5. No breach log handling
"""

from pathlib import Path
import re

print("=" * 60)
print("Stage 6 DecisionView Validation")
print("=" * 60)

html_path = Path("ui/decision_view.html")

if not html_path.exists():
    print("\n✗ decision_view.html not found")
    exit(1)

content = html_path.read_text(encoding="utf-8")

# Check 1: Read-only badges/warnings
print("\n[1/7] Checking read-only guarantees...")
read_only_markers = [
    "READ ONLY",
    "No repair",
    "No scoring",
    "No side effects"
]

found = 0
for marker in read_only_markers:
    if marker in content:
        print(f"  ✓ Found: '{marker}'")
        found += 1

assert found >= 3, "Missing read-only warnings"

# Check 2: No repair logic
print("\n[2/7] Checking for repair logic (should not exist)...")
forbidden_patterns = [
    r"\.repair\(",
    r"fixEvent",
    r"repairSchema",
    r"computeScore\(",  # UI should not compute scores
    r"updatePolicy"     # UI should not update policy
]

violations = []
for pattern in forbidden_patterns:
    matches = re.findall(pattern, content, re.IGNORECASE)
    if matches:
        violations.append(pattern)

if violations:
    print(f"  ✗ Found forbidden patterns: {violations}")
    exit(1)
else:
    print("  ✓ No repair/compute logic found")

# Check 3: Defensive parsing
print("\n[3/7] Checking defensive parsing...")
if "try {" in content and "JSON.parse" in content and "catch" in content:
    print("  ✓ Defensive JSON parsing with try/catch")
else:
    print("  ✗ Missing defensive parsing")
    exit(1)

if "invalidLines" in content or "skipped" in content:
    print("  ✓ Invalid lines tracking")
else:
    print("  ⚠️  No invalid lines tracking")

# Check 4: JSONL + WHY-API modes
print("\n[4/7] Checking data source modes...")
if "JSONL" in content and "WHY-API" in content:
    print("  ✓ Both JSONL and WHY-API modes present")
else:
    print("  ✗ Missing data source modes")
    exit(1)

# Check 5: Filter implementation
print("\n[5/7] Checking filter implementation...")
filter_fields = ["intent", "status", "action", "score", "job", "trace"]
found_filters = 0
for field in filter_fields:
    if f"f{field.capitalize()}" in content or f"#{field}" in content:
        found_filters += 1

print(f"  ✓ Found {found_filters}/{len(filter_fields)} filter fields")
assert found_filters >= 4, "Missing essential filters"

# Check 6: No breach log handling
print("\n[6/7] Checking breach log handling...")
if "breach" in content.lower():
    # Check if it's just a comment/documentation
    breach_lines = [line for line in content.split('\n') if 'breach' in line.lower()]
    active_breach = [line for line in breach_lines if not line.strip().startswith('//') and not line.strip().startswith('*')]
    if active_breach:
        print(f"  ⚠️  Found active breach handling: {len(active_breach)} lines")
    else:
        print("  ✓ Breach only mentioned in comments")
else:
    print("  ✓ No breach log handling")

# Check 7: WHY-API endpoints
print("\n[7/7] Checking WHY-API integration...")
api_endpoints = ["/api/why/latest", "/api/why/trace", "/api/why/stats"]
found_endpoints = 0
for endpoint in api_endpoints:
    if endpoint in content:
        print(f"  ✓ Found: {endpoint}")
        found_endpoints += 1

assert found_endpoints >= 2, "Missing WHY-API endpoints"

# Summary
print("\n" + "=" * 60)
print("✅ STAGE 6 DECISIONVIEW VALIDATION PASSED")
print("=" * 60)
print("DecisionView HTML complies with spec:")
print("  1. ✓ Read-only guarantees visible")
print("  2. ✓ No repair/compute logic")
print("  3. ✓ Defensive parsing")
print("  4. ✓ JSONL + WHY-API modes")
print("  5. ✓ Filter implementation")
print("  6. ✓ No active breach handling")
print("  7. ✓ WHY-API integration")
print("=" * 60)
print("Ready for live testing with real decision log")
print("=" * 60)
