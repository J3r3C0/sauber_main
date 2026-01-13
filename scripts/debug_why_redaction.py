"""Quick debug test for WHY-API redaction"""

from core.why_api import sanitize

# Test event with sensitive fields
test_event = {
    "prompt": "SHOULD_BE_REDACTED",
    "body": "X" * 5000,
    "normal_field": "ok"
}

result = sanitize(test_event)

print("Original prompt:", test_event.get("prompt"))
print("Sanitized prompt:", result.get("prompt"))
print("Expected:", "***REDACTED***")
print("Match:", result.get("prompt") == "***REDACTED***")

print("\nOriginal body length:", len(test_event.get("body", "")))
print("Sanitized body length:", len(result.get("body", "")))
print("Ends with truncated:", result.get("body", "").endswith("...(truncated)"))

print("\nNormal field:", result.get("normal_field"))
