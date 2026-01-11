from __future__ import annotations

from typing import Any, Dict

from .config import GateConfig
from .models import GateReport, GateResult, GateStatus, Severity, NextAction, Reason, Suggestion
from .utils import utc_now_iso


def run_g2_allowlist_kind(job: Dict[str, Any], cfg: GateConfig) -> GateResult:
    kind = str(job.get("kind", "")).strip()
    report = GateReport(
        gate_id="G2_ALLOWLIST_KIND",
        status=GateStatus.PASS,
        severity=Severity.LOW,
        evidence={"job_id": job.get("job_id"), "kind": kind},
        timestamp_utc=utc_now_iso(),
    )

    if not kind:
        report.status = GateStatus.FAIL
        report.severity = Severity.MEDIUM
        report.reasons.append(Reason("MISSING_KIND", "kind is required."))
        report.next_action = NextAction.REQUIRE_LLM2
        return GateResult(report)

    if kind in cfg.forbidden_kinds:
        report.status = GateStatus.PAUSE
        report.severity = Severity.HIGH
        report.reasons.append(Reason("KIND_FORBIDDEN", f"kind '{kind}' is explicitly forbidden."))
        # Suggest constrained alternative
        alt = "FILE_WRITE" if "WRITE" in kind or "EXEC" in kind else "NOOP"
        report.suggestions.append(Suggestion(
            type="PATCH_JOB",
            patch=[{"op": "replace", "path": "/kind", "value": alt}],
            why=f"Replace forbidden kind with constrained alternative '{alt}'."
        ))
        report.next_action = NextAction.QUARANTINE
        return GateResult(report)

    if kind not in cfg.allowlisted_kinds:
        report.status = GateStatus.FAIL
        report.severity = Severity.MEDIUM
        report.reasons.append(Reason("KIND_NOT_ALLOWLISTED", f"kind '{kind}' is not allowlisted."))
        report.suggestions.append(Suggestion(
            type="ADVICE",
            explanation=f"Choose one of allowlisted kinds: {sorted(cfg.allowlisted_kinds)}"
        ))
        report.next_action = NextAction.REQUIRE_LLM2
        return GateResult(report)

    if kind in cfg.manual_only_kinds:
        report.status = GateStatus.WARN
        report.severity = Severity.MEDIUM
        report.reasons.append(Reason("KIND_MANUAL_ONLY", f"kind '{kind}' requires operator ACK."))
        report.next_action = NextAction.REQUIRE_OPERATOR_ACK
        return GateResult(report)

    return GateResult(report)
