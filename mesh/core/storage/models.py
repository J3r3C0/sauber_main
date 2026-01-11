# sheratan_core_v2/models.py
# Production-safe dataclass models for Pydantic v2 + FastAPI
# :contentReference[oaicite:1]{index=1}

from enum import Enum
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid


# ------------------------------------------------------------------------------
# CONSTANTS & ENUMS
# ------------------------------------------------------------------------------

class JobStatus(str, Enum):
    PENDING = "pending"
    DISPATCHED = "dispatched"
    CLAIMED = "claimed"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class JobExecState(str, Enum):
    """
    Deterministic job execution states for gate/audit flow.
    Every job must have exactly one final state.
    """
    PROPOSED = "PROPOSED"           # Initial submission
    GATED = "GATED"                 # Gates evaluated
    EMITTED = "EMITTED"             # Approved, sent to runtime/input
    AUDIT_PENDING = "AUDIT_PENDING" # Waiting for LLM2
    QUARANTINED = "QUARANTINED"     # PAUSE decision
    MANUAL_REVIEW = "MANUAL_REVIEW" # Requires operator
    REMEDIATION_FAILED = "REMEDIATION_FAILED"  # Patch illegal/failed
    FAILED = "FAILED"               # Unrecoverable error


@dataclass
class JobEvent:
    """Append-only event record for a job."""
    id: str
    job_id: str
    type: str  # JOB_CREATED, AUCTION_STARTED, CLAIMED, STARTED, FINISHED, FAILED
    timestamp: str
    host_id: Optional[str] = None
    attempt_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def create(job_id: str, event_type: str, host_id: Optional[str] = None, attempt_id: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> "JobEvent":
        return JobEvent(
            id=str(uuid.uuid4()),
            job_id=job_id,
            type=event_type,
            timestamp=datetime.utcnow().isoformat() + "Z",
            host_id=host_id,
            attempt_id=attempt_id,
            metadata=metadata or {}
        )


# ------------------------------------------------------------------------------
# MISSION
# ------------------------------------------------------------------------------

@dataclass
class MissionCreate:
    """Payload used to create a mission."""
    title: str
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)


@dataclass
class Mission:
    """Persistent mission model."""
    id: str
    title: str
    description: str
    metadata: Dict[str, Any]
    tags: List[str]
    created_at: str

    @staticmethod
    def from_create(m: MissionCreate) -> "Mission":
        return Mission(
            id=str(uuid.uuid4()),
            title=m.title,
            description=m.description,
            metadata=m.metadata or {},
            tags=m.tags or [],
            created_at=datetime.utcnow().isoformat() + "Z",
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ------------------------------------------------------------------------------
# TASK
# ------------------------------------------------------------------------------

@dataclass
class TaskCreate:
    """Input for task creation."""
    name: str
    description: str
    kind: str
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Task:
    """Persistent task model."""
    id: str
    mission_id: str
    name: str
    description: str
    kind: str
    params: Dict[str, Any]
    created_at: str

    @staticmethod
    def from_create(mission_id: str, t: TaskCreate) -> "Task":
        return Task(
            id=str(uuid.uuid4()),
            mission_id=mission_id,
            name=t.name,
            description=t.description,
            kind=t.kind,
            params=t.params or {},
            created_at=datetime.utcnow().isoformat() + "Z",
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ------------------------------------------------------------------------------
# JOB
# ------------------------------------------------------------------------------

@dataclass
class JobCreate:
    """Payload for job creation (task execution request)."""
    payload: Dict[str, Any]


@dataclass
class Job:
    """
    Persistent job model.
    Acts as JobSpec (immutable description of the task).
    Status and state history are tracked via Events.
    """
    id: str
    task_id: str
    payload: Dict[str, Any]
    status: str  # Current snapshot status
    result: Optional[Dict[str, Any]]
    created_at: str
    updated_at: str
    constraints: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0

    @staticmethod
    def from_create(task_id: str, j: JobCreate) -> "Job":
        ts = datetime.utcnow().isoformat() + "Z"
        return Job(
            id=str(uuid.uuid4()),
            task_id=task_id,
            payload=j.payload or {},
            status=JobStatus.PENDING,
            result=None,
            created_at=ts,
            updated_at=ts,
            constraints=j.payload.get("constraints", {}),
            priority=j.payload.get("priority", 0)
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

