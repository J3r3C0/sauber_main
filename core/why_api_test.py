# core/why_api_test.py
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.testclient import TestClient

from .why_api import router as why_router


def _write_jsonl(path: Path, rows: list[Dict[str, Any]]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def run():
    # Setup app
    app = FastAPI()
    app.include_router(why_router, prefix="/api/why")
    client = TestClient(app)

    # Temp log
    tmp_log = Path("runtime/tmp_decision_trace.jsonl")
    # Minimal schema-like event (not validated here; WHY-API is read-only)
    ev = {
        "schema_version": "decision_trace_v1",
        "timestamp": "2026-01-13T05:10:00Z",
        "trace_id": "t1",
        "node_id": "n1",
        "parent_node_id": None,
        "intent": "dispatch_job",
        "build_id": "main",
        "job_id": "job_1",
        "depth": 0,
        "state": {"context_refs": [], "constraints": {}},
        "action": {"action_id": "a1", "type": "ROUTE", "mode": "execute", "params": {}, "select_score": 1.0, "risk_gate": True},
        "result": {"status": "success", "metrics": {"latency_ms": 1}, "score": 1.0, "error": {"code": "E_TEST", "message": "x"}, "artifacts": []},
        "prompt": "SHOULD_BE_REDACTED",
        "body": "X" * 5000
    }
    _write_jsonl(tmp_log, [ev])

    # latest
    r = client.get("/api/why/latest", params={"log_path": str(tmp_log), "intent": "dispatch_job", "max_lines": 2000})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert data["event"].get("prompt") == "***REDACTED***"
    assert isinstance(data["event"].get("body"), str) and data["event"]["body"].endswith("...(truncated)")

    # trace
    r = client.get("/api/why/trace/t1", params={"log_path": str(tmp_log)})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert data["trace_id"] == "t1"
    assert len(data["events"]) == 1

    # job
    r = client.get("/api/why/job/job_1", params={"log_path": str(tmp_log)})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert "t1" in data["trace_ids"]

    # stats
    r = client.get("/api/why/stats", params={"log_path": str(tmp_log), "intent": "dispatch_job", "window_lines": 10000})
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    assert data["stats"]["count"] == 1

    print("[✓] WHY-API smoke tests passed.")


if __name__ == "__main__":
    run()
