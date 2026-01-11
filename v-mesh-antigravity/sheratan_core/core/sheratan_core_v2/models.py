# sheratan_core_v2/models.py
# Production-safe dataclass models for Pydantic v2 + FastAPI
# :contentReference[oaicite:1]{index=1}

from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid


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
    """Persistent job model."""
    id: str
    task_id: str
    payload: Dict[str, Any]
    status: str
    result: Optional[Dict[str, Any]]
    created_at: str
    updated_at: str

    @staticmethod
    def from_create(task_id: str, j: JobCreate) -> "Job":
        ts = datetime.utcnow().isoformat() + "Z"
        return Job(
            id=str(uuid.uuid4()),
            task_id=task_id,
            payload=j.payload or {},
            status="pending",
            result=None,
            created_at=ts,
            updated_at=ts,
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

