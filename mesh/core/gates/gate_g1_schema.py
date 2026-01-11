from __future__ import annotations

from typing import Any, Dict, List

from .models import GateReport, GateResult, GateStatus, Severity, NextAction, Reason, Suggestion
from .utils import utc_now_iso, is_uuid_like


REQUIRED_TOP_LEVEL = ["job_id", "kind", "action", "params", "provenance"]


def run_g1_parse_validate(job: Dict[str, Any]) -> GateResult:
    report = GateReport(
        gate_id="G1_PARSE_VALIDATE",
        status=GateStatus.PASS,
        severity=Severity.LOW,
        evidence={"job_id": job.get("job_id"), "kind": job.get("kind")},
        timestamp_utc=utc_now_iso(),
    )

    missing: List[str] = [k for k in REQUIRED_TOP_LEVEL if k not in job]
    if missing:
        report.status = GateStatus.FAIL
        report.severity = Severity.MEDIUM
        report.reasons.append(Reason("MISSING_FIELDS", f"Missing required fields: {missing}"))
        report.suggestions.append(Suggestion(
            type="PATCH_JOB",
            patch=[{"op": "add", "path": f"/{k}", "value": "" if k in ("job_id","kind","action") else {}}
                   for k in missing],
            why="Add required fields to match job schema."
        ))
        report.next_action = NextAction.REQUIRE_LLM2
        return GateResult(report)

    if not isinstance(job.get("params"), dict):
        report.status = GateStatus.FAIL
        report.severity = Severity.MEDIUM
        report.reasons.append(Reason("PARAMS_NOT_OBJECT", "params must be an object/dict."))
        report.suggestions.append(Suggestion(
            type="PATCH_JOB",
            patch=[{"op": "replace", "path": "/params", "value": {}}],
            why="Ensure params is a dict."
        ))
        report.next_action = NextAction.REQUIRE_LLM2
        return GateResult(report)

    prov = job.get("provenance")
    if not isinstance(prov, dict):
        report.status = GateStatus.FAIL
        report.severity = Severity.MEDIUM
        report.reasons.append(Reason("PROVENANCE_NOT_OBJECT", "provenance must be an object/dict."))
        report.suggestions.append(Suggestion(
            type="PATCH_JOB",
            patch=[{"op": "replace", "path": "/provenance", "value": {"source_zone": "narrative"}}],
            why="Ensure provenance exists and contains source_zone."
        ))
        report.next_action = NextAction.REQUIRE_LLM2
        return GateResult(report)

    job_id = str(job.get("job_id", ""))
    if not is_uuid_like(job_id):
        report.status = GateStatus.WARN
        report.severity = Severity.LOW
        report.reasons.append(Reason("JOB_ID_NOT_UUID", "job_id is not UUID-like; recommend UUID."))
        report.suggestions.append(Suggestion(
            type="ADVICE",
            explanation="Generate a UUID for job_id to support replay/audit."
        ))
        # WARN still allows continuation
        report.next_action = NextAction.ALLOW

    return GateResult(report)
