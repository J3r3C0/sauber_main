"""
WHY-API Redaction Test

Verifies that WHY-API will not leak sensitive data.
Tests redaction rules before implementing the actual API.
"""

import json
import re
from typing import Dict, Any

# Denylist for sensitive keys
DENY_KEYS = {
    "token", "secret", "password", "authorization", "cookie", 
    "api_key", "apikey", "prompt", "body", "key"
}

def should_redact_key(key: str) -> bool:
    """Check if key should be redacted"""
    key_lower = key.lower()
    
    # Check exact matches and substrings
    for deny in DENY_KEYS:
        if deny in key_lower:
            return True
    
    return False

def redact_event(event: Dict[str, Any], max_length: int = 2000) -> Dict[str, Any]:
    """
    Redact sensitive fields and truncate long values.
    
    Rules:
    - Redact keys containing: token, secret, password, etc.
    - Truncate string values > max_length
    - Keep paths relative (no absolute paths)
    """
    def redact_value(k: str, v: Any) -> Any:
        # Redact sensitive keys
        if should_redact_key(k):
            return "[REDACTED]"
        
        # Handle strings
        if isinstance(v, str):
            # Truncate long strings
            if len(v) > max_length:
                return v[:max_length] + "..."
            # Remove absolute paths (Windows: C:\, Unix: /home/, /root/)
            if re.match(r'^[A-Za-z]:[\\\/]|^/(?:home|root)/', v):
                return "[PATH_REDACTED]"
            return v
        
        # Recurse into dicts
        if isinstance(v, dict):
            return {k2: redact_value(k2, v2) for k2, v2 in v.items()}
        
        # Recurse into lists
        if isinstance(v, list):
            return [redact_value(k, item) if isinstance(item, (dict, str)) else item for item in v]
        
        return v
    
    return {k: redact_value(k, v) for k, v in event.items()}

# Test cases
test_event = {
    "trace_id": "abc123",
    "action": {
        "params": {
            "api_key": "sk-1234567890",
            "worker_id": "local_worker",
            "prompt": "secret prompt content",
            "file_path": "C:\\Users\\user\\secrets.txt"
        }
    },
    "result": {
        "artifacts": ["/home/user/output.json"],
        "long_text": "x" * 3000
    }
}

print("=" * 60)
print("WHY-API Redaction Test")
print("=" * 60)

redacted = redact_event(test_event)

print("\nOriginal:")
print(json.dumps(test_event, indent=2)[:500])

print("\nRedacted:")
print(json.dumps(redacted, indent=2))

# Verify redaction
assert redacted["action"]["params"]["api_key"] == "[REDACTED]"
assert redacted["action"]["params"]["prompt"] == "[REDACTED]"
assert redacted["action"]["params"]["file_path"] == "[PATH_REDACTED]"
assert redacted["result"]["artifacts"][0] == "[PATH_REDACTED]"
assert len(redacted["result"]["long_text"]) <= 2003  # 2000 + "..."

print("\n✓ All redaction rules working correctly")
print("=" * 60)
