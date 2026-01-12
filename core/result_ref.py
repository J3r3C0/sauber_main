from typing import Any, Dict, Optional

def safe_get(obj: Any, json_path: str, default: Any = None) -> Any:
    """
    Very small JSONPath-like: dot separated, supports numeric indices with [i] style.
    Examples: "files.foo.content", "items[0].name"
    """
    cur = obj
    if not json_path:
        return cur
    # Replace [ with .[ to treat indices as segments
    parts = json_path.replace("[", ".[").split(".")
    for part in parts:
        if part == "":
            continue
        if part.startswith("[") and part.endswith("]"):
            try:
                idx = int(part[1:-1])
                # Check if cur is a list or similar sequence
                cur = cur[idx]
            except Exception:
                return default
        else:
            if isinstance(cur, dict) and part in cur:
                cur = cur[part]
            else:
                return default
    return cur

def apply_transform(value: Any, transform: Optional[Dict[str, Any]]) -> Any:
    """Apply specific transformations to an extracted value."""
    if not transform:
        return value
    op = transform.get("op")
    if op == "take_first":
        n = int(transform.get("n", 20))
        return value[:n] if isinstance(value, list) else value
    if op == "unique":
        if isinstance(value, list):
            seen = set()
            out = []
            for v in value:
                if v not in seen:
                    # Note: this assumes v is hashable; might need json.dumps for complex items
                    try:
                        seen.add(v)
                        out.append(v)
                    except TypeError:
                        # Fallback for non-hashable items
                        out.append(v)
            return out
        return value
    if op == "filter_suffix":
        suffixes = transform.get("suffixes", [])
        if isinstance(value, list):
            return [v for v in value if isinstance(v, str) and any(v.endswith(s) for s in suffixes)]
        return value
    return value
