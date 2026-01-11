# sheratan_core_v2/storage.py

"""
Storage 2.0 - SQLite-based persistence.
Replaces the old JSONL storage for better scalability, transactions, and features.
"""

from __future__ import annotations
import json
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime

from core import config, models
from core.database import get_db, init_db

# Re-expose DATA_DIR for main.py compatibility
DATA_DIR = config.DATA_DIR

# ------------------------------------------------------------------------------
# INITIALIZATION & MIGRATION
# ------------------------------------------------------------------------------

def migrate_if_needed():
    """
    Checks if JSONL files exist and DB is empty.
    If so, migrates data to SQLite and renames old files.
    """
    MISSIONS_FILE = config.DATA_DIR / "missions.jsonl"
    TASKS_FILE = config.DATA_DIR / "tasks.jsonl"
    JOBS_FILE = config.DATA_DIR / "jobs.jsonl"

    def row_exists(table):
        with get_db() as conn:
            return conn.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone() is not None

    if not (MISSIONS_FILE.exists() or TASKS_FILE.exists() or JOBS_FILE.exists()):
        return

    # If any JSONL exists and DB is empty, migrate
    if not row_exists("missions"):
        print("[storage] Migrating JSONL data to SQLite...")
        
        # Helper to read JSONL
        def read_jsonl(path):
            if not path.exists(): return []
            rows = []
            with path.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip(): rows.append(json.loads(line))
            return rows

        with get_db() as conn:
            # Migrate Missions
            for m in read_jsonl(MISSIONS_FILE):
                conn.execute("""
                    INSERT INTO missions (id, title, description, user_id, status, metadata, tags, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (m['id'], m['title'], m['description'], m['user_id'], m.get('status', 'planned'), json.dumps(m['metadata']), json.dumps(m['tags']), m['created_at']))
            
            # Migrate Tasks
            for t in read_jsonl(TASKS_FILE):
                conn.execute("""
                    INSERT INTO tasks (id, mission_id, name, description, kind, params, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (t['id'], t['mission_id'], t['name'], t['description'], t['kind'], json.dumps(t['params']), t['created_at']))
            
            # Migrate Jobs
            for j in read_jsonl(JOBS_FILE):
                conn.execute("""
                    INSERT INTO jobs (id, task_id, payload, status, result, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (j['id'], j['task_id'], json.dumps(j['payload']), j['status'], json.dumps(j['result']) if j['result'] else None, j['created_at'], j['updated_at']))
            
            conn.commit()
            print("[storage] Migration complete.")

        # Rename old files to .bak
        for f in [MISSIONS_FILE, TASKS_FILE, JOBS_FILE]:
            if f.exists():
                f.rename(f.with_suffix(".jsonl.bak"))

# Initialize DB on import
init_db()
migrate_if_needed()

# ------------------------------------------------------------------------------
# MISSIONS - CRUD
# ------------------------------------------------------------------------------

def list_missions() -> List[models.Mission]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM missions ORDER BY created_at DESC").fetchall()
        return [
            models.Mission(
                id=r['id'],
                title=r['title'],
                description=r['description'],
                user_id=r['user_id'],
                status=r['status'],
                metadata=json.loads(r['metadata']),
                tags=json.loads(r['tags']),
                created_at=r['created_at']
            ) for r in rows
        ]

def get_mission(mission_id: str) -> Optional[models.Mission]:
    with get_db() as conn:
        r = conn.execute("SELECT * FROM missions WHERE id = ?", (mission_id,)).fetchone()
        if not r: return None
        return models.Mission(
            id=r['id'],
            title=r['title'],
            description=r['description'],
            user_id=r['user_id'],
            status=r['status'],
            metadata=json.loads(r['metadata']),
            tags=json.loads(r['tags']),
            created_at=r['created_at']
        )

def create_mission(mission: models.Mission) -> models.Mission:
    with get_db() as conn:
        conn.execute("""
            INSERT INTO missions (id, title, description, user_id, status, metadata, tags, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (mission.id, mission.title, mission.description, mission.user_id, mission.status, json.dumps(mission.metadata), json.dumps(mission.tags), mission.created_at))
        conn.commit()
    return mission

def update_mission(mission: models.Mission) -> None:
    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO missions (id, title, description, user_id, status, metadata, tags, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (mission.id, mission.title, mission.description, mission.user_id, mission.status, json.dumps(mission.metadata), json.dumps(mission.tags), mission.created_at))
        conn.commit()

def delete_mission(mission_id: str) -> bool:
    with get_db() as conn:
        # Cascading delete handles tasks and jobs if schema has ON DELETE CASCADE
        # SQLite needs PRAGMA foreign_keys = ON;
        conn.execute("PRAGMA foreign_keys = ON")
        res = conn.execute("DELETE FROM missions WHERE id = ?", (mission_id,))
        conn.commit()
        return res.rowcount > 0

# ------------------------------------------------------------------------------
# TASKS - CRUD
# ------------------------------------------------------------------------------

def list_tasks() -> List[models.Task]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM tasks ORDER BY created_at ASC").fetchall()
        return [
            models.Task(
                id=r['id'],
                mission_id=r['mission_id'],
                name=r['name'],
                description=r['description'],
                kind=r['kind'],
                params=json.loads(r['params']),
                created_at=r['created_at']
            ) for r in rows
        ]

def get_task(task_id: str) -> Optional[models.Task]:
    with get_db() as conn:
        r = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not r: return None
        return models.Task(
            id=r['id'],
            mission_id=r['mission_id'],
            name=r['name'],
            description=r['description'],
            kind=r['kind'],
            params=json.loads(r['params']),
            created_at=r['created_at']
        )

def create_task(task: models.Task) -> models.Task:
    with get_db() as conn:
        conn.execute("""
            INSERT INTO tasks (id, mission_id, name, description, kind, params, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (task.id, task.mission_id, task.name, task.description, task.kind, json.dumps(task.params), task.created_at))
        conn.commit()
    return task

def update_task(task: models.Task) -> None:
    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO tasks (id, mission_id, name, description, kind, params, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (task.id, task.mission_id, task.name, task.description, task.kind, json.dumps(task.params), task.created_at))
        conn.commit()

def find_task_by_name(mission_id: str, name: str) -> Optional[models.Task]:
    with get_db() as conn:
        r = conn.execute("SELECT * FROM tasks WHERE mission_id = ? AND name = ?", (mission_id, name)).fetchone()
        if not r: return None
        return models.Task(
            id=r['id'],
            mission_id=r['mission_id'],
            name=r['name'],
            description=r['description'],
            kind=r['kind'],
            params=json.loads(r['params']),
            created_at=r['created_at']
        )

# ------------------------------------------------------------------------------
# JOBS - CRUD
# ------------------------------------------------------------------------------

def list_jobs() -> List[models.Job]:
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM jobs ORDER BY created_at ASC").fetchall()
        return [
            models.Job(
                id=r['id'],
                task_id=r['task_id'],
                payload=json.loads(r['payload']),
                status=r['status'],
                result=json.loads(r['result']) if r['result'] else None,
                retry_count=r['retry_count'],
                idempotency_key=r['idempotency_key'],
                priority=r['priority'],
                timeout_seconds=r['timeout_seconds'],
                depends_on=json.loads(r['depends_on']),
                created_at=r['created_at'],
                updated_at=r['updated_at']
            ) for r in rows
        ]
    return jobs

def get_job(job_id: str) -> Optional[models.Job]:
    with get_db() as conn:
        r = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if r:
            return models.Job(
                id=r['id'],
                task_id=r['task_id'],
                payload=json.loads(r['payload']),
                status=r['status'],
                result=json.loads(r['result']) if r['result'] else None,
                retry_count=r['retry_count'],
                idempotency_key=r['idempotency_key'],
                priority=r['priority'],
                timeout_seconds=r['timeout_seconds'],
                depends_on=json.loads(r['depends_on']),
                created_at=r['created_at'],
                updated_at=r['updated_at']
            )
    return None

def create_job(job: models.Job) -> models.Job:
    with get_db() as conn:
        conn.execute("""
            INSERT INTO jobs (id, task_id, payload, status, result, retry_count, idempotency_key, priority, timeout_seconds, depends_on, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job.id, job.task_id, json.dumps(job.payload), job.status, 
            json.dumps(job.result) if job.result else None, job.retry_count,
            job.idempotency_key, job.priority, job.timeout_seconds, json.dumps(job.depends_on),
            job.created_at, job.updated_at
        ))
        conn.commit()
    return job

def update_job(job: models.Job) -> None:
    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO jobs (id, task_id, payload, status, result, retry_count, idempotency_key, priority, timeout_seconds, depends_on, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job.id, job.task_id, json.dumps(job.payload), job.status, 
            json.dumps(job.result) if job.result else None, job.retry_count,
            job.idempotency_key, job.priority, job.timeout_seconds, json.dumps(job.depends_on),
            job.created_at, job.updated_at
        ))
        conn.commit()

# --- Rate Limit Config CRUD ---

def get_rate_limit_config(source: str) -> Optional[dict]:
    with get_db() as conn:
        r = conn.execute("SELECT * FROM rate_limit_config WHERE source = ?", (source,)).fetchone()
        if r:
            return dict(r)
    return None

def update_rate_limit_config(source: str, max_jobs_per_minute: int, max_concurrent_jobs: int, current_count: int, window_start: str):
    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO rate_limit_config (source, max_jobs_per_minute, max_concurrent_jobs, current_count, window_start)
            VALUES (?, ?, ?, ?, ?)
        """, (source, max_jobs_per_minute, max_concurrent_jobs, current_count, window_start))
        conn.commit()

def count_running_jobs_by_source(source: str) -> int:
    # Note: In our current simple setup, we might need to join with missions/tasks to find 'source'
    # For now, let's assume 'source' is passed as metadata or we filter by something else.
    # Alternatively, we can just count all 'working/running' jobs if there's only one source.
    # For a real multi-source rate limiter, we'd need 'source' on the Job or Task.
    with get_db() as conn:
        r = conn.execute("SELECT COUNT(*) FROM jobs WHERE status IN ('working', 'running')").fetchone()
        return r[0]
