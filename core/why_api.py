# core/why_api.py
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

from .why_reader import latest_event, trace_by_id, traces_by_job_id, stats, sanitize


# IMPORTANT: This module must be READ-ONLY (zero side effects).
# - no writes
# - no priors updates
# - no log mutation

DEFAULT_LOG_PATH = "logs/decision_trace.jsonl"

router = APIRouter(tags=["why"])


@router.get("/latest")
def why_latest(
    intent: Optional[str] = Query(default=None),
    log_path: str = Query(default=DEFAULT_LOG_PATH),
    max_lines: int = Query(default=2000, ge=1, le=200000),
):
    ev, meta = latest_event(log_path, intent=intent, max_lines=max_lines)
    if ev is None:
        return JSONResponse({"ok": False, "error": "not_found", "meta": meta.__dict__}, status_code=404)
    return {"ok": True, "event": sanitize(ev), "meta": meta.__dict__}


@router.get("/trace/{trace_id}")
def why_trace(
    trace_id: str,
    log_path: str = Query(default=DEFAULT_LOG_PATH),
    max_lines: int = Query(default=10000, ge=1, le=500000),
):
    events, meta = trace_by_id(log_path, trace_id=trace_id, max_lines=max_lines)
    if not events:
        return JSONResponse({"ok": False, "error": "not_found", "meta": meta.__dict__}, status_code=404)
    return {"ok": True, "trace_id": trace_id, "events": sanitize(events), "meta": meta.__dict__}


@router.get("/job/{job_id}")
def why_job(
    job_id: str,
    log_path: str = Query(default=DEFAULT_LOG_PATH),
    max_lines: int = Query(default=10000, ge=1, le=500000),
):
    trace_ids, meta = traces_by_job_id(log_path, job_id=job_id, max_lines=max_lines)
    if not trace_ids:
        return JSONResponse({"ok": False, "error": "not_found", "meta": meta.__dict__}, status_code=404)
    return {"ok": True, "job_id": job_id, "trace_ids": trace_ids, "meta": meta.__dict__}


@router.get("/stats")
def why_stats(
    intent: Optional[str] = Query(default=None),
    log_path: str = Query(default=DEFAULT_LOG_PATH),
    window_lines: int = Query(default=10000, ge=1, le=500000),
):
    s, meta = stats(log_path, intent=intent, window_lines=window_lines)
    return {"ok": True, "intent": intent, "stats": s, "meta": meta.__dict__}
