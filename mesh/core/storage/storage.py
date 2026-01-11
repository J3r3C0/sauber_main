# sheratan_core_v2/storage.py

"""
Storage 2.0 - Production-ready JSONL-based persistence with file-locking.

Implements all required CRUD operations for Missions, Tasks, and Jobs.
Thread-safe through FileLock mechanism.
"""

from __future__ import annotations
import json
import os
import time
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, List, Optional

from . import config, models


# ------------------------------------------------------------------------------
# CONFIGURATION
# ------------------------------------------------------------------------------

DATA_DIR = config.DATA_DIR
MISSIONS_FILE = DATA_DIR / "missions.jsonl"
TASKS_FILE = DATA_DIR / "tasks.jsonl"
JOBS_FILE = DATA_DIR / "jobs.jsonl"
JOBS_EVENTS_FILE = DATA_DIR / "job_events.jsonl"

LOCK_RETRY_DELAY = 0.05  # 50ms
LOCK_TIMEOUT = 10.0      # 10s


# ------------------------------------------------------------------------------
# FILE-LOCK MECHANISM (Thread-Safe)
# ------------------------------------------------------------------------------

class FileLock:
    """
    Simple file-based lock for atomic read-modify-write operations.
    Uses OS-level exclusive file creation (O_CREAT | O_EXCL).
    """
    
    def __init__(self, path: Path):
        self.path = path
        self.lockfile = path.with_suffix(path.suffix + ".lock")
    
    def __enter__(self):
        start = time.time()
        while True:
            try:
                # Try to create lock file exclusively
                fd = os.open(str(self.lockfile), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                os.close(fd)
                break
            except FileExistsError:
                # Lock exists, retry with delay
                if time.time() - start > LOCK_TIMEOUT:
                    raise TimeoutError(f"Could not acquire lock for {self.path} after {LOCK_TIMEOUT}s")
                time.sleep(LOCK_RETRY_DELAY)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        try:
            self.lockfile.unlink(missing_ok=True)
        except Exception:
            pass  # Best effort cleanup


# ------------------------------------------------------------------------------
# JSONL HELPERS
# ------------------------------------------------------------------------------

def _iter_jsonl(path: Path) -> Iterable[dict]:
    """
    Lazily iterate over JSONL file, yielding parsed JSON objects.
    Skips empty lines and invalid JSON.
    """
    if not path.exists():
        return
    
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                # Skip corrupted lines
                continue


def _write_all_jsonl(path: Path, rows: List[dict]) -> None:
    """
    Atomically write all rows to JSONL file.
    Creates parent directories if needed.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


# ------------------------------------------------------------------------------
# MISSIONS - CRUD
# ------------------------------------------------------------------------------

def list_missions() -> List[models.Mission]:
    """List all missions from storage."""
    return [models.Mission(**row) for row in _iter_jsonl(MISSIONS_FILE)]


def get_mission(mission_id: str) -> Optional[models.Mission]:
    """Get a specific mission by ID."""
    for m in list_missions():
        if m.id == mission_id:
            return m
    return None


def create_mission(mission: models.Mission) -> models.Mission:
    """
    Create a new mission.
    Thread-safe through file locking.
    """
    with FileLock(MISSIONS_FILE):
        rows = list(_iter_jsonl(MISSIONS_FILE))
        rows.append(asdict(mission))
        _write_all_jsonl(MISSIONS_FILE, rows)
    return mission


def update_mission(mission: models.Mission) -> None:
    """
    Update an existing mission.
    If mission doesn't exist, creates it.
    Thread-safe through file locking.
    """
    with FileLock(MISSIONS_FILE):
        rows = list(_iter_jsonl(MISSIONS_FILE))
        new_rows = []
        found = False
        
        for row in rows:
            if row.get("id") == mission.id:
                new_rows.append(asdict(mission))
                found = True
            else:
                new_rows.append(row)
        
        # If not found, append
        if not found:
            new_rows.append(asdict(mission))
        
        _write_all_jsonl(MISSIONS_FILE, new_rows)


def delete_mission(mission_id: str) -> bool:
    """
    Delete a mission and all its related tasks and jobs.
    Returns True if mission was found and deleted.
    Thread-safe through file locking.
    """
    # First, find all tasks for this mission
    task_ids = set()
    for t in list_tasks():
        if t.mission_id == mission_id:
            task_ids.add(t.id)
    
    # Delete jobs belonging to those tasks
    if task_ids:
        with FileLock(JOBS_FILE):
            rows = list(_iter_jsonl(JOBS_FILE))
            new_rows = [row for row in rows if row.get("task_id") not in task_ids]
            _write_all_jsonl(JOBS_FILE, new_rows)
    
    # Delete tasks for this mission
    with FileLock(TASKS_FILE):
        rows = list(_iter_jsonl(TASKS_FILE))
        new_rows = [row for row in rows if row.get("mission_id") != mission_id]
        _write_all_jsonl(TASKS_FILE, new_rows)
    
    # Delete the mission itself
    with FileLock(MISSIONS_FILE):
        rows = list(_iter_jsonl(MISSIONS_FILE))
        new_rows = [row for row in rows if row.get("id") != mission_id]
        if len(new_rows) == len(rows):
            return False  # Mission not found
        _write_all_jsonl(MISSIONS_FILE, new_rows)
    
    return True


# ------------------------------------------------------------------------------
# TASKS - CRUD
# ------------------------------------------------------------------------------

def list_tasks() -> List[models.Task]:
    """List all tasks from storage."""
    return [models.Task(**row) for row in _iter_jsonl(TASKS_FILE)]


def get_task(task_id: str) -> Optional[models.Task]:
    """Get a specific task by ID."""
    for t in list_tasks():
        if t.id == task_id:
            return t
    return None


def create_task(task: models.Task) -> models.Task:
    """
    Create a new task.
    Thread-safe through file locking.
    """
    with FileLock(TASKS_FILE):
        rows = list(_iter_jsonl(TASKS_FILE))
        rows.append(asdict(task))
        _write_all_jsonl(TASKS_FILE, rows)
    return task


def update_task(task: models.Task) -> None:
    """
    Update an existing task.
    If task doesn't exist, creates it.
    Thread-safe through file locking.
    """
    with FileLock(TASKS_FILE):
        rows = list(_iter_jsonl(TASKS_FILE))
        new_rows = []
        found = False
        
        for row in rows:
            if row.get("id") == task.id:
                new_rows.append(asdict(task))
                found = True
            else:
                new_rows.append(row)
        
        if not found:
            new_rows.append(asdict(task))
        
        _write_all_jsonl(TASKS_FILE, new_rows)


def find_task_by_name(mission_id: str, name: str) -> Optional[models.Task]:
    """
    Find a task by name within a specific mission.
    Critical for LCP action interpreter!
    """
    for t in list_tasks():
        if t.mission_id == mission_id and t.name == name:
            return t
    return None


# ------------------------------------------------------------------------------
# JOBS - CRUD
# ------------------------------------------------------------------------------

def list_jobs() -> List[models.Job]:
    """List all jobs from storage with backward compatibility for legacy fields."""
    valid_fields = {'id', 'task_id', 'payload', 'status', 'result', 'created_at', 'updated_at', 'constraints', 'priority'}
    jobs = []
    for row in _iter_jsonl(JOBS_FILE):
        # Filter out legacy fields (job_id, supersedes_job_id, reissued_at, etc.)
        filtered_row = {k: v for k, v in row.items() if k in valid_fields}
        jobs.append(models.Job(**filtered_row))
    return jobs


def list_jobs_deduplicated() -> List[models.Job]:
    """
    List jobs with deduplication for research jobs.
    
    "Latest Wins" Strategy:
    - For research jobs with same job_id, keep only the latest
    - Latest determined by reissued_at (if present) or created_at
    - Non-research jobs (UUID-only) are kept as-is
    
    Returns list of Job objects with only latest versions.
    """
    all_jobs = list(_iter_jsonl(JOBS_FILE))
    
    # Deduplicate: latest wins per job_id
    latest_by_key = {}
    
    for row in all_jobs:
        job_id = row.get('job_id')
        
        # Research job: has semantic job_id
        if job_id and isinstance(job_id, str) and job_id.startswith('job:'):
            existing = latest_by_key.get(job_id)
            
            if not existing:
                latest_by_key[job_id] = row
            else:
                # Compare timestamps (reissued_at takes precedence)
                existing_ts = existing.get('reissued_at', existing.get('created_at', ''))
                current_ts = row.get('reissued_at', row.get('created_at', ''))
                
                if current_ts > existing_ts:
                    latest_by_key[job_id] = row
        else:
            # Non-research job: use UUID id as key
            uuid_id = row.get('id')
            if uuid_id:
                latest_by_key[uuid_id] = row
    
    # Convert to Job objects (filter to only expected fields)
    job_fields = {'id', 'task_id', 'payload', 'status', 'result', 'created_at', 'updated_at', 'constraints', 'priority'}
    jobs = []
    for row in latest_by_key.values():
        # Filter to only fields that Job model expects
        filtered = {k: v for k, v in row.items() if k in job_fields}
        # Ensure required fields have defaults
        filtered.setdefault('constraints', {})
        filtered.setdefault('priority', 0)
        try:
            jobs.append(models.Job(**filtered))
        except Exception as e:
            # Log and skip malformed jobs
            print(f"Warning: Skipping malformed job: {e}")
            continue
    return jobs


def get_job(job_id: str) -> Optional[models.Job]:
    """Get a specific job by ID."""
    for j in list_jobs():
        if j.id == job_id:
            return j
    return None


def create_job(job: models.Job) -> models.Job:
    """
    Create a new job.
    Thread-safe through file locking.
    """
    # Write to JSONL
    with FileLock(JOBS_FILE):
        with open(JOBS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(job)) + "\n")
    
    # Emit initial event
    create_job_event(models.JobEvent.create(
        job_id=job.id,
        event_type="JOB_CREATED",
        metadata={"task_id": job.task_id}
    ))
    return job


def update_job(job: models.Job) -> None:
    """
    Update an existing job.
    If job doesn't exist, creates it.
    Thread-safe through file locking.
    
    IMPORTANT: Caller should update job.updated_at before calling this!
    """
    with FileLock(JOBS_FILE):
        rows = list(_iter_jsonl(JOBS_FILE))
        new_rows = []
        found = False
        
        for row in rows:
            if row.get("id") == job.id:
                new_rows.append(asdict(job))
                found = True
            else:
                new_rows.append(row)
        
        if not found:
            new_rows.append(asdict(job))
        
        _write_all_jsonl(JOBS_FILE, new_rows)


def delete_job(job_id: str) -> bool:
    """
    Delete a specific job by ID.
    Returns True if job was found and deleted, False otherwise.
    Thread-safe through file locking.
    """
    with FileLock(JOBS_FILE):
        rows = list(_iter_jsonl(JOBS_FILE))
        new_rows = [row for row in rows if row.get("id") != job_id]
        if len(new_rows) == len(rows):
            return False  # Job not found
        _write_all_jsonl(JOBS_FILE, new_rows)
    return len(new_rows) != len(rows)


# ------------------------------------------------------------------------------
# JOB EVENTS (The History)
# ------------------------------------------------------------------------------

def create_job_event(event: models.JobEvent) -> None:
    """Append a new event to the job history."""
    with FileLock(JOBS_EVENTS_FILE):
        with open(JOBS_EVENTS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(event)) + "\n")


def get_job_history(job_id: str) -> List[models.JobEvent]:
    """Retrieve all events for a specific job."""
    events = []
    for row in _iter_jsonl(JOBS_EVENTS_FILE):
        if row.get("job_id") == job_id:
            events.append(models.JobEvent(**row))
    return sorted(events, key=lambda e: e.timestamp)
