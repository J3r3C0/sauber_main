from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class GateStatus(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"
    PAUSE = "PAUSE"


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class NextAction(str, Enum):
    ALLOW = "ALLOW"
    REQUIRE_LLM2 = "REQUIRE_LLM2"
    REQUIRE_OPERATOR_ACK = "REQUIRE_OPERATOR_ACK"
    QUARANTINE = "QUARANTINE"


@dataclass
class Reason:
    code: str
    message: str


@dataclass
class Suggestion:
    type: str  # e.g. PATCH_JOB, ADVICE
    patch: Optional[List[Dict[str, Any]]] = None  # RFC6902-like ops
    why: Optional[str] = None
    explanation: Optional[str] = None


@dataclass
class GateReport:
    gate_id: str
    status: GateStatus
    severity: Severity
    reasons: List[Reason] = field(default_factory=list)
    evidence: Dict[str, Any] = field(default_factory=dict)
    suggestions: List[Suggestion] = field(default_factory=list)
    next_action: NextAction = NextAction.ALLOW
    timestamp_utc: str = ""


@dataclass
class GateResult:
    """Convenience wrapper for pipeline aggregation."""
    report: GateReport

    @property
    def status(self) -> GateStatus:
        return self.report.status
