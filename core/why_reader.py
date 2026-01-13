# core/why_reader.py
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class WhyMeta:
    scanned_lines: int
    returned: int
    skipped_invalid_lines: int


def _iter_lines_tail(path: Path, max_lines: int) -> Tuple[List[str], int]:
    """
    Simple, deterministic tail by reading all lines then slicing.
    OK for bounded windows (e.g. 2000/10000) and avoids platform-specific seek hacks.
    Returns (lines, total_lines).
    """
    if not path.exists():
        return ([], 0)
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    total = len(lines)
    if max_lines <= 0:
        return ([], total)
    return (lines[-max_lines:], total)


def _parse_json_lines(lines: Iterable[str]) -> Tuple[List[Dict[str, Any]], int]:
    out: List[Dict[str, Any]] = []
    skipped = 0
    for ln in lines:
        ln = ln.strip()
        if not ln:
            continue
        try:
            out.append(json.loads(ln))
        except Exception:
            skipped += 1
    return out, skipped


def tail_events(log_path: str, max_lines: int = 2000) -> Tuple[List[Dict[str, Any]], WhyMeta]:
    p = Path(log_path)
    lines, _total = _iter_lines_tail(p, max_lines=max_lines)
    events, skipped = _parse_json_lines(lines)
    meta = WhyMeta(scanned_lines=len(lines), returned=len(events), skipped_invalid_lines=skipped)
    return events, meta


def latest_event(
    log_path: str,
    intent: Optional[str] = None,
    max_lines: int = 2000,
) -> Tuple[Optional[Dict[str, Any]], WhyMeta]:
    events, meta = tail_events(log_path, max_lines=max_lines)
    if intent:
        events = [e for e in events if e.get("intent") == intent]
        meta = WhyMeta(scanned_lines=meta.scanned_lines, returned=len(events), skipped_invalid_lines=meta.skipped_invalid_lines)
    if not events:
        return None, meta
    # Assumes timestamp is ISO date-time; lexicographic sort works for Zulu timestamps.
    events.sort(key=lambda e: str(e.get("timestamp", "")))
    return events[-1], meta


def trace_by_id(log_path: str, trace_id: str, max_lines: int = 10000) -> Tuple[List[Dict[str, Any]], WhyMeta]:
    events, meta = tail_events(log_path, max_lines=max_lines)
    filtered = [e for e in events if e.get("trace_id") == trace_id]
    # Stable ordering: timestamp then depth
    filtered.sort(key=lambda e: (str(e.get("timestamp", "")), int(e.get("depth", 0))))
    meta = WhyMeta(scanned_lines=meta.scanned_lines, returned=len(filtered), skipped_invalid_lines=meta.skipped_invalid_lines)
    return filtered, meta


def traces_by_job_id(log_path: str, job_id: str, max_lines: int = 10000) -> Tuple[List[str], WhyMeta]:
    events, meta = tail_events(log_path, max_lines=max_lines)
    trace_ids = []
    for e in events:
        if e.get("job_id") == job_id and e.get("trace_id"):
            trace_ids.append(str(e["trace_id"]))
    # Unique, stable order: newest first by first occurrence from the tail window
    seen = set()
    uniq: List[str] = []
    for tid in reversed(trace_ids):
        if tid in seen:
            continue
        seen.add(tid)
        uniq.append(tid)
    meta = WhyMeta(scanned_lines=meta.scanned_lines, returned=len(uniq), skipped_invalid_lines=meta.skipped_invalid_lines)
    return uniq, meta


def stats(
    log_path: str,
    intent: Optional[str] = None,
    window_lines: int = 10000,
) -> Tuple[Dict[str, Any], WhyMeta]:
    events, meta = tail_events(log_path, max_lines=window_lines)
    if intent:
        events = [e for e in events if e.get("intent") == intent]
    meta = WhyMeta(scanned_lines=meta.scanned_lines, returned=len(events), skipped_invalid_lines=meta.skipped_invalid_lines)

    if not events:
        return {
            "count": 0,
            "success_rate": 0.0,
            "mean_score": 0.0,
            "top_action_types": [],
            "top_error_codes": [],
        }, meta

    count = len(events)
    successes = 0
    scores: List[float] = []
    action_types = Counter()
    error_codes = Counter()

    for e in events:
        res = e.get("result") or {}
        status = str(res.get("status") or "")
        if status in ("success", "recovered", "partial"):
            successes += 1
        try:
            scores.append(float(res.get("score", 0.0)))
        except Exception:
            scores.append(0.0)

        act = e.get("action") or {}
        if act.get("type"):
            action_types[str(act["type"])] += 1

        err = res.get("error") or {}
        if isinstance(err, dict) and err.get("code"):
            error_codes[str(err["code"])] += 1

    mean_score = sum(scores) / max(1, len(scores))
    success_rate = successes / max(1, count)

    return {
        "count": count,
        "success_rate": round(success_rate, 4),
        "mean_score": round(mean_score, 4),
        "top_action_types": action_types.most_common(10),
        "top_error_codes": error_codes.most_common(10),
    }, meta


# --- Sanitization (Response-Only) ---

MAX_TRUNC_CHARS = 2000

# Conservative denylist (exact keys, case-insensitive match)
DENY_KEYS = {
    "token", "secret", "password", "authorization", "cookie", "api_key",
    "prompt", "body"
}


def _truncate_str(s: str, limit: int = MAX_TRUNC_CHARS) -> str:
    if s is None:
        return s
    if len(s) <= limit:
        return s
    return s[:limit] + "...(truncated)"


def _should_redact_key(k: str) -> bool:
    return str(k).strip().lower() in DENY_KEYS


def _redact_value(_: str) -> str:
    return "***REDACTED***"


def sanitize(obj: Any) -> Any:
    """
    Recursively redact sensitive keys and truncate long strings.
    Response-only sanitation. MUST NOT be used to mutate stored logs.
    """
    if isinstance(obj, dict):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            if _should_redact_key(k):
                out[k] = _redact_value(str(k))
            else:
                out[k] = sanitize(v)
        return out
    if isinstance(obj, list):
        return [sanitize(x) for x in obj]
    if isinstance(obj, str):
        return _truncate_str(obj)
    return obj

