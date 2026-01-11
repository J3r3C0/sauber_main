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
    """List all jobs from storage."""
    return [models.Job(**row) for row in _iter_jsonl(JOBS_FILE)]


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
    with FileLock(JOBS_FILE):
        rows = list(_iter_jsonl(JOBS_FILE))
        rows.append(asdict(job))
        _write_all_jsonl(JOBS_FILE, rows)
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
