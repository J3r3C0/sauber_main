from __future__ import annotations

from typing import Any, Dict

from .config import GateConfig
from .models import GateReport, GateResult, GateStatus, Severity, NextAction, Reason
from .utils import utc_now_iso, iter_text_fields, json_dumps_compact


def run_g4_escalation_detect(job: Dict[str, Any], cfg: GateConfig) -> GateResult:
    report = GateReport(
        gate_id="G4_ESCALATION_DETECT",
        status=GateStatus.PASS,
        severity=Severity.LOW,
        evidence={"job_id": job.get("job_id"), "kind": job.get("kind")},
        timestamp_utc=utc_now_iso(),
    )

    all_text = " | ".join([t.lower() for t in iter_text_fields(job) if isinstance(t, str)])

    # Hard markers => PAUSE
    for m in (cfg.escalation_hard_markers or []):
        if m.lower() in all_text:
            report.status = GateStatus.PAUSE
            report.severity = Severity.HIGH
            report.reasons.append(Reason("HARD_MARKER", f"Hard escalation marker detected: '{m}'"))
            report.next_action = NextAction.QUARANTINE
            return GateResult(report)

    # Soft markers => WARN
    for m in (cfg.escalation_soft_markers or []):
        if m.lower() in all_text:
            report.status = GateStatus.WARN
            report.severity = Severity.MEDIUM
            report.reasons.append(Reason("SOFT_MARKER", f"Soft escalation marker detected: '{m}'"))
            report.next_action = NextAction.REQUIRE_LLM2
            return GateResult(report)

    # Patch size heuristic (if present)
    patch_ops = job.get("params", {}).get("patch")
    if isinstance(patch_ops, list) and len(patch_ops) > cfg.max_patch_ops:
        report.status = GateStatus.PAUSE
        report.severity = Severity.HIGH
        report.reasons.append(Reason("PATCH_TOO_LARGE", f"Patch has {len(patch_ops)} ops; max is {cfg.max_patch_ops}"))
        report.next_action = NextAction.QUARANTINE
        return GateResult(report)

    return GateResult(report)
