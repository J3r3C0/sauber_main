from __future__ import annotations

from typing import Any, Dict

from .models import GateReport, GateResult, GateStatus, Severity, NextAction, Reason
from .utils import utc_now_iso


def run_g0_quarantine_barrier(job: Dict[str, Any]) -> GateResult:
    """
    Flow barrier:
    - blocks direct OUTPUT -> INPUT conversion.
    - validates provenance.source_zone is one of allowed.
    """
    source_zone = (job.get("provenance") or {}).get("source_zone", "")
    report = GateReport(
        gate_id="G0_QUARANTINE_BARRIER",
        status=GateStatus.PASS,
        severity=Severity.LOW,
        evidence={"job_id": job.get("job_id"), "source_zone": source_zone},
        timestamp_utc=utc_now_iso(),
    )

    if not source_zone:
        report.status = GateStatus.FAIL
        report.severity = Severity.MEDIUM
        report.reasons.append(Reason("MISSING_SOURCE_ZONE", "provenance.source_zone is required."))
        report.next_action = NextAction.REQUIRE_LLM2
        return GateResult(report)

    # Core rule: nothing from output is executable directly
    if source_zone == "output":
        report.status = GateStatus.PAUSE
        report.severity = Severity.HIGH
        report.reasons.append(Reason("OUTPUT_TO_INPUT_BLOCKED", "Jobs originating from output are never executable."))
        report.next_action = NextAction.QUARANTINE
        return GateResult(report)

    # narrative is allowed to continue, but still must pass G1-G4
    if source_zone in ("narrative", "input", "quarantine"):
        report.status = GateStatus.PASS
        report.next_action = NextAction.ALLOW
        return GateResult(report)

    report.status = GateStatus.FAIL
    report.severity = Severity.MEDIUM
    report.reasons.append(Reason("UNKNOWN_SOURCE_ZONE", f"Unknown source_zone '{source_zone}'."))
    report.next_action = NextAction.REQUIRE_LLM2
    return GateResult(report)
