from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .config import GateConfig
from .models import GateReport, GateStatus, NextAction
from .gate_g0_barrier import run_g0_quarantine_barrier
from .gate_g1_schema import run_g1_parse_validate
from .gate_g2_allowlist import run_g2_allowlist_kind
from .gate_g3_path_sandbox import run_g3_path_sandbox
from .gate_g4_escalation import run_g4_escalation_detect


def run_gates_v1(job: Dict[str, Any], cfg: GateConfig) -> List[GateReport]:
    reports: List[GateReport] = []

    r0 = run_g0_quarantine_barrier(job).report
    reports.append(r0)
    if r0.status in (GateStatus.FAIL, GateStatus.PAUSE):
        return reports

    r1 = run_g1_parse_validate(job).report
    reports.append(r1)
    if r1.status in (GateStatus.FAIL, GateStatus.PAUSE):
        return reports

    r2 = run_g2_allowlist_kind(job, cfg).report
    reports.append(r2)
    if r2.status in (GateStatus.FAIL, GateStatus.PAUSE):
        return reports

    r3 = run_g3_path_sandbox(job, cfg).report
    reports.append(r3)
    if r3.status in (GateStatus.FAIL, GateStatus.PAUSE):
        return reports

    r4 = run_g4_escalation_detect(job, cfg).report
    reports.append(r4)
    # WARN is allowed to proceed; FAIL/PAUSE stops
    return reports


def final_decision(reports: List[GateReport]) -> Tuple[str, NextAction]:
    """
    Returns:
      - overall_status: PASS|WARN|FAIL|PAUSE
      - strongest_next_action
    """
    if any(r.status == GateStatus.PAUSE for r in reports):
        # strongest
        na = [r.next_action for r in reports if r.status == GateStatus.PAUSE][-1]
        return "PAUSE", na
    if any(r.status == GateStatus.FAIL for r in reports):
        na = [r.next_action for r in reports if r.status == GateStatus.FAIL][-1]
        return "FAIL", na
    if any(r.status == GateStatus.WARN for r in reports):
        na = [r.next_action for r in reports if r.status == GateStatus.WARN][-1]
        return "WARN", na
    return "PASS", NextAction.ALLOW
