from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def safe_get(d: Dict[str, Any], path: List[str], default=None):
    cur = d
    for key in path:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def is_uuid_like(s: str) -> bool:
    return bool(re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", s or ""))


def iter_text_fields(obj: Any) -> Iterable[str]:
    """Yield all string values found in nested dict/list for escalation scanning."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from iter_text_fields(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from iter_text_fields(v)


def normalize_rel_path(p: str) -> str:
    # convert backslashes, strip leading ./, collapse multiple slashes
    s = (p or "").replace("\\", "/").strip()
    while s.startswith("./"):
        s = s[2:]
    s = re.sub(r"/+", "/", s)
    return s


def is_absolute_path_like(p: str) -> bool:
    s = (p or "").strip()
    if not s:
        return False
    # Windows drive: C:\ or C:/
    if re.match(r"^[A-Za-z]:[\\/]", s):
        return True
    # UNC path \\server\share
    if s.startswith("\\\\"):
        return True
    # Unix absolute
    if s.startswith("/"):
        return True
    return False


def has_parent_traversal(p: str) -> bool:
    s = normalize_rel_path(p)
    parts = [x for x in s.split("/") if x]
    return any(part == ".." for part in parts)


def resolve_under_roots(project_root: Path, roots: List[Path], rel_path: str) -> Tuple[bool, Path]:
    """Resolve rel_path and ensure it stays under one of roots."""
    rel = normalize_rel_path(rel_path)
    target = (project_root / rel).resolve()
    for r in roots:
        rr = r.resolve()
        try:
            target.relative_to(rr)
            return True, target
        except Exception:
            continue
    return False, target


def json_dumps_compact(x: Any) -> str:
    return json.dumps(x, ensure_ascii=False, separators=(",", ":"))
