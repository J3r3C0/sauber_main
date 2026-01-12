from pydantic import BaseModel, Field
from datetime import datetime
from typing import Dict, Any, List, Optional
import uuid

# ------------------------------------------------------------------------------
# LOOP STATE (Self-Loop System)
# ------------------------------------------------------------------------------

class LoopMetrics(BaseModel):
    """Metrics captured per loop iteration."""
    tasks_completed: int = 0
    error_count: int = 0
    progress_delta: float = 0.0
    loop_duration_ms: int = 0
    human_feedback_score: Optional[int] = None  # 0-100

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class LoopState(BaseModel):
    """Extended loop state for Self-Loop iterations."""
    iteration: int = 1
    history_summary: str = ""
    open_questions: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    # Extended fields
    actions_taken: List[str] = Field(default_factory=list)
    problems_identified: List[str] = Field(default_factory=list)
    metric_history: List[Dict[str, Any]] = Field(default_factory=list)
    
    def add_iteration(
        self,
        action: str,
        result_summary: str,
        metrics: Optional[LoopMetrics] = None,
        new_questions: Optional[List[str]] = None,
        new_problems: Optional[List[str]] = None
    ) -> "LoopState":
        """Create new LoopState for next iteration with updated history."""
        updated_history = f"{self.history_summary}\n[Iteration {self.iteration}] {action}: {result_summary}".strip()
        
        new_state = LoopState(
            iteration=self.iteration + 1,
            history_summary=updated_history,
            open_questions=new_questions if new_questions else self.open_questions.copy(),
            constraints=self.constraints.copy(),
            actions_taken=self.actions_taken + [action],
            problems_identified=self.problems_identified + (new_problems or []),
            metric_history=self.metric_history + ([metrics.model_dump()] if metrics else [])
        )
        return new_state
    
    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "LoopState":
        """Create LoopState from dictionary (for loading from JSON)."""
        return LoopState(**data)


# ------------------------------------------------------------------------------
# MISSION
# ------------------------------------------------------------------------------

class MissionCreate(BaseModel):
    """Payload used to create a mission."""
    title: str
    description: str
    user_id: str = "alice"  # Target for ledger charging
    status: str = "planned"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class Mission(BaseModel):
    """Persistent mission model."""
    id: str
    title: str
    description: str
    user_id: str
    status: str = "planned"
    metadata: Dict[str, Any]
    tags: List[str]
    created_at: str

    @staticmethod
    def from_create(m: MissionCreate) -> "Mission":
        return Mission(
            id=str(uuid.uuid4()),
            title=m.title,
            description=m.description,
            user_id=m.user_id,
            status=m.status or "planned",
            metadata=m.metadata or {},
            tags=m.tags or [],
            created_at=datetime.utcnow().isoformat() + "Z",
        )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


# ------------------------------------------------------------------------------
# TASK
# ------------------------------------------------------------------------------

class TaskCreate(BaseModel):
    """Input for task creation."""
    name: str
    description: str = ""
    kind: str = ""
    params: Dict[str, Any] = Field(default_factory=dict)


class Task(BaseModel):
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
            params=t.params,
            created_at=datetime.utcnow().isoformat() + "Z",
        )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


# ------------------------------------------------------------------------------
# JOB
# ------------------------------------------------------------------------------

class JobCreate(BaseModel):
    """Payload for job creation (task execution request)."""
    payload: Dict[str, Any]
    priority: str = "normal"
    timeout_seconds: int = 300
    depends_on: List[str] = []
    idempotency_key: Optional[str] = None


class Job(BaseModel):
    """Persistent job model."""
    id: str
    task_id: str
    payload: Dict[str, Any]
    status: str
    result: Optional[Dict[str, Any]] = None
    retry_count: int = 0
    idempotency_key: Optional[str] = None
    priority: str = "normal"  # normal, high, critical
    timeout_seconds: int = 300
    depends_on: List[str] = []
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
            retry_count=0,
            created_at=ts,
            updated_at=ts,
        )

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


# ------------------------------------------------------------------------------
# PHASE 10.1: CHAIN MODELS
# ------------------------------------------------------------------------------

class ChainContext(BaseModel):
    """Context and artifacts for an autonomous chain."""
    chain_id: str
    task_id: str
    state: str = "running"  # running, done, error
    limits: Dict[str, Any] = Field(default_factory=lambda: {
        "max_files": 50,
        "max_total_bytes": 200_000,
        "max_bytes_per_file": 50_000,
    })
    artifacts: Dict[str, Any] = Field(default_factory=dict)
    error: Optional[Dict[str, Any]] = None
    needs_tick: int = 0
    last_tick_at: Optional[str] = None
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()


class ChainSpec(BaseModel):
    """Specification for a follow-up job in a chain."""
    spec_id: str
    chain_id: str
    task_id: str
    root_job_id: str
    parent_job_id: str
    kind: str
    params: Dict[str, Any]
    resolved_params: Optional[Dict[str, Any]] = None
    resolved: bool = False
    status: str = "pending"  # pending, dispatched, done, failed
    dedupe_key: str
    claim_id: Optional[str] = None
    claimed_until: Optional[str] = None
    dispatched_job_id: Optional[str] = None
    created_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump()

