from __future__ import annotations

from typing import Any, Dict, List, Tuple

from .config import GateConfig
from .models import GateReport, GateResult, GateStatus, Severity, NextAction, Reason, Suggestion
from .utils import utc_now_iso, is_absolute_path_like, has_parent_traversal, normalize_rel_path, resolve_under_roots


PATH_KEYS = [
    # Common param keys to treat as paths
    ("params", "path"),
    ("params", "target_path"),
    ("params", "file_path"),
    ("params", "filepath"),
    ("params", "dir"),
    ("params", "directory"),
]


def run_g3_path_sandbox(job: Dict[str, Any], cfg: GateConfig) -> GateResult:
    report = GateReport(
        gate_id="G3_PATH_SANDBOX",
        status=GateStatus.PASS,
        severity=Severity.LOW,
        evidence={"job_id": job.get("job_id"), "kind": job.get("kind")},
        timestamp_utc=utc_now_iso(),
    )

    params = job.get("params") or {}
    found_paths: List[Tuple[str, str]] = []

    for a, b in PATH_KEYS:
        if isinstance(params, dict) and b in params:
            v = params.get(b)
            if isinstance(v, str) and v.strip():
                found_paths.append((f"/params/{b}", v))

    # If no paths, pass
    if not found_paths:
        return GateResult(report)

    for json_path, p in found_paths:
        p_norm = normalize_rel_path(p)

        # Absolute path => PAUSE (exfil / wrong root)
        if is_absolute_path_like(p):
            report.status = GateStatus.PAUSE
            report.severity = Severity.HIGH
            report.reasons.append(Reason("ABSOLUTE_PATH", f"Absolute path is not allowed: {p}"))
            report.suggestions.append(Suggestion(
                type="PATCH_JOB",
                patch=[{"op": "replace", "path": json_path, "value": p_norm.lstrip("/") or "workspace/"}],
                why="Rewrite into project-scoped relative path."
            ))
            report.next_action = NextAction.QUARANTINE
            return GateResult(report)

        # .. traversal => FAIL (repairable)
        if has_parent_traversal(p):
            report.status = GateStatus.FAIL
            report.severity = Severity.HIGH
            report.reasons.append(Reason("PATH_TRAVERSAL", f"Parent traversal '..' is not allowed: {p}"))
            report.suggestions.append(Suggestion(
                type="PATCH_JOB",
                patch=[{"op": "replace", "path": json_path, "value": p_norm.replace("..", "").strip("/") }],
                why="Remove traversal and target a safe relative path."
            ))
            report.next_action = NextAction.REQUIRE_LLM2
            return GateResult(report)

        # Forbidden prefixes (relative)
        for pref in (cfg.forbidden_rel_prefixes or []):
            if p_norm == pref.rstrip("/") or p_norm.startswith(pref):
                report.status = GateStatus.PAUSE
                report.severity = Severity.HIGH
                report.reasons.append(Reason("FORBIDDEN_PREFIX", f"Path targets forbidden area '{pref}': {p_norm}"))
                report.next_action = NextAction.QUARANTINE
                return GateResult(report)

        # Must resolve under workspace roots
        ok, resolved = resolve_under_roots(cfg.project_root, cfg.workspace_roots or [cfg.project_root], p_norm)
        if not ok:
            report.status = GateStatus.PAUSE
            report.severity = Severity.HIGH
            report.reasons.append(Reason("OUTSIDE_WORKSPACE", f"Resolved path is outside workspace roots: {resolved}"))
            report.next_action = NextAction.QUARANTINE
            return GateResult(report)

    return GateResult(report)
