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
        return create_job_with_conn(conn, job)

def create_job_with_conn(conn, job: models.Job) -> models.Job:
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
    
    # --- TRACE ON DB WRITE (deterministic, path-independent) ---
    # Log trace whenever job status changes to completed/failed
    if job.status in ["completed", "failed"]:
        try:
            from core.decision_trace import trace_logger
            import os
            import uuid
            
            trace_logger.log_node(
                trace_id=f"db-write-{job.id}",
                intent="job_status_change",
                build_id=os.getenv("SHERATAN_BUILD_ID", "main-v2"),
                job_id=job.id,
                depth=0,
                state={
                    "context_refs": [f"job:{job.id}"],
                    "constraints": {
                        "budget_remaining": 100,
                        "risk_level": "low"
                    }
                },
                action={
                    "action_id": str(uuid.uuid4()),
                    "type": "EXECUTE",
                    "mode": "execute",
                    "params": {
                        "status": job.status,
                        "kind": job.payload.get("kind", "unknown") if isinstance(job.payload, dict) else "unknown"
                    },
                    "select_score": 1.0,
                    "risk_gate": True
                },
                result={
                    "status": "success" if job.status == "completed" else "failed",
                    "metrics": {
                        "retry_count": job.retry_count
                    },
                    "score": 1.0 if job.status == "completed" else 0.0
                }
            )
        except Exception as trace_err:
            # Never fail job update due to trace error
            print(f"[storage] Warning: Failed to log trace on DB write: {trace_err}")

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

# ------------------------------------------------------------------------------
# PHASE 10.1: CHAIN CONTEXT & SPECS
# ------------------------------------------------------------------------------

import hashlib
from datetime import timezone

def _now_iso() -> str:
    """Return current UTC timestamp in ISO format."""
    return datetime.now(timezone.utc).isoformat()

def _json_dumps(obj: Any) -> str:
    """Canonical JSON serialization (deterministic)."""
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))

def _json_loads(s: str) -> Any:
    """Safe JSON deserialization."""
    return json.loads(s) if s else None

def _hash_dedupe_key(data: Dict[str, Any]) -> str:
    """Generate deterministic hash for deduplication."""
    raw = _json_dumps(data).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()

# --- Chain Context Store API ---

def ensure_chain_context(
    conn,
    chain_id: str,
    task_id: str,
    limits: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Idempotent: creates chain_context row if not exists.
    Returns the stored context dict.
    """
    limits = limits or {
        "max_files": 50,
        "max_total_bytes": 200_000,
        "max_bytes_per_file": 50_000,
    }
    now = _now_iso()
    conn.execute(
        """
        INSERT OR IGNORE INTO chain_context
        (chain_id, task_id, state, limits_json, artifacts_json, error_json, needs_tick, created_at, updated_at)
        VALUES (?, ?, 'running', ?, ?, NULL, 0, ?, ?)
        """,
        (chain_id, task_id, _json_dumps(limits), _json_dumps({}), now, now),
    )
    conn.commit()
    return get_chain_context(conn, chain_id)

def get_chain_context(conn, chain_id: str) -> Optional[Dict[str, Any]]:
    """Load chain context from DB."""
    row = conn.execute(
        "SELECT chain_id, task_id, state, limits_json, artifacts_json, error_json, needs_tick FROM chain_context WHERE chain_id=?",
        (chain_id,),
    ).fetchone()
    if not row:
        return None
    return {
        "chain_id": row[0],
        "task_id": row[1],
        "state": row[2],
        "limits": _json_loads(row[3]) or {},
        "artifacts": _json_loads(row[4]) or {},
        "error": _json_loads(row[5]) if row[5] else None,
        "needs_tick": int(row[6] or 0),
    }

def list_chains_by_mission(conn, mission_id: str) -> List[Dict[str, Any]]:
    """List all chain contexts associated with tasks of a given mission."""
    rows = conn.execute(
        """
        SELECT cc.chain_id, cc.task_id, cc.state, cc.limits_json, cc.artifacts_json, cc.error_json, cc.needs_tick 
        FROM chain_context cc
        JOIN tasks t ON cc.task_id = t.id
        WHERE t.mission_id = ?
        """,
        (mission_id,),
    ).fetchall()
    
    results = []
    for row in rows:
        results.append({
            "chain_id": row[0],
            "task_id": row[1],
            "state": row[2],
            "limits": _json_loads(row[3]) or {},
            "artifacts": _json_loads(row[4]) or {},
            "error": _json_loads(row[5]) if row[5] else None,
            "needs_tick": int(row[6] or 0),
        })
    return results

def set_chain_state(conn, chain_id: str, state: str, error: Optional[Dict[str, Any]] = None) -> None:
    """Update chain state."""
    now = _now_iso()
    conn.execute(
        "UPDATE chain_context SET state=?, error_json=?, updated_at=? WHERE chain_id=?",
        (state, _json_dumps(error) if error else None, now, chain_id),
    )
    conn.commit()

def set_chain_needs_tick(conn, chain_id: str, needs_tick: bool) -> None:
    """Set needs_tick flag for chain runner."""
    now = _now_iso()
    conn.execute(
        "UPDATE chain_context SET needs_tick=?, updated_at=? WHERE chain_id=?",
        (1 if needs_tick else 0, now, chain_id),
    )
    conn.commit()

def set_chain_artifact(
    conn,
    chain_id: str,
    key: str,
    value: Any,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Enforces limits based on chain_context.limits.
    Stores artifacts_json as { key: { "value": ..., "meta": ... }, ... }
    Returns updated context dict.
    """
    ctx = get_chain_context(conn, chain_id)
    if not ctx:
        raise ValueError(f"chain_context not found for chain_id={chain_id}")

    limits = ctx["limits"] or {}
    artifacts = ctx["artifacts"] or {}

    meta = meta or {}
    meta.setdefault("schema_version", 1)
    meta.setdefault("created_at", _now_iso())

    # enforce minimal caps for known keys
    if key == "file_list":
        max_files = int(limits.get("max_files", 50))
        if isinstance(value, list):
            meta["count_before"] = len(value)
            if len(value) > max_files:
                meta["truncated"] = True
                value = value[:max_files]
            meta["count"] = len(value)

    if key == "file_blobs":
        max_total = int(limits.get("max_total_bytes", 200_000))
        max_per = int(limits.get("max_bytes_per_file", 50_000))
        total = 0
        truncated_any = False
        if isinstance(value, dict):
            # Calculate total bytes before truncation (handle both dict and string values)
            total_before = 0
            for v in value.values():
                if isinstance(v, dict):
                    content = v.get("content", "")
                    total_before += len(str(content).encode("utf-8"))
                elif isinstance(v, str):
                    total_before += len(v.encode("utf-8"))
            meta["total_bytes_before"] = total_before
            
            newv = {}
            for p, rec in value.items():
                # Handle both dict and string values
                if isinstance(rec, dict):
                    content = rec.get("content", "")
                    b = content.encode("utf-8")
                    if len(b) > max_per:
                        truncated_any = True
                        b = b[:max_per]
                        rec = {**rec, "content": b.decode("utf-8", errors="ignore"), "truncated": True}
                elif isinstance(rec, str):
                    # If rec is a string, treat it as content directly
                    b = rec.encode("utf-8")
                    if len(b) > max_per:
                        truncated_any = True
                        b = b[:max_per]
                        rec = {"content": b.decode("utf-8", errors="ignore"), "truncated": True}
                    else:
                        rec = {"content": rec}
                else:
                    # Skip invalid types
                    continue
                    
                if total + len(b) > max_total:
                    truncated_any = True
                    break
                total += len(b)
                newv[p] = rec
            value = newv
        meta["total_bytes"] = total
        if truncated_any:
            meta["truncated"] = True

    artifacts[key] = {"value": value, "meta": meta}

    now = _now_iso()
    conn.execute(
        "UPDATE chain_context SET artifacts_json=?, updated_at=? WHERE chain_id=?",
        (_json_dumps(artifacts), now, chain_id),
    )
    conn.commit()
    return get_chain_context(conn, chain_id)  # updated

# --- Chain Specs Store API ---

def append_chain_specs(
    conn,
    chain_id: str,
    task_id: str,
    root_job_id: str,
    parent_job_id: str,
    specs: List[Dict[str, Any]],
) -> List[str]:
    """
    Inserts specs as pending; dedupe via UNIQUE(chain_id, dedupe_key).
    Returns spec_ids that were inserted (new ones).
    """
    import uuid
    now = _now_iso()
    inserted: List[str] = []

    for s in specs:
        kind = s.get("kind") or s.get("type")  # tolerate both
        params = s.get("params") if isinstance(s.get("params"), dict) else {k: v for k, v in s.items() if k not in ("kind", "type")}
        dedupe_key = _hash_dedupe_key({"parent_job_id": parent_job_id, "kind": kind, "params": params})

        spec_id = s.get("spec_id") or uuid.uuid4().hex

        try:
            conn.execute(
                """
                INSERT INTO chain_specs
                (spec_id, chain_id, task_id, root_job_id, parent_job_id, kind, params_json,
                 resolved_params_json, resolved, status, dedupe_key, dispatched_job_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, NULL, 0, 'pending', ?, NULL, ?, ?)
                """,
                (spec_id, chain_id, task_id, root_job_id, parent_job_id, kind, _json_dumps(params), dedupe_key, now, now),
            )
            inserted.append(spec_id)
        except Exception:
            # likely UNIQUE constraint hit => deduped
            continue

    conn.commit()
    return inserted

def list_pending_chain_specs(conn, chain_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Get all pending specs for a chain."""
    rows = conn.execute(
        """
        SELECT spec_id, task_id, root_job_id, parent_job_id, kind, params_json, resolved_params_json, resolved, status, dedupe_key, claim_id, claimed_until, dispatched_job_id
        FROM chain_specs
        WHERE chain_id=? AND status='pending'
        ORDER BY created_at ASC
        LIMIT ?
        """,
        (chain_id, limit),
    ).fetchall()

    out = []
    for r in rows:
        out.append({
            "spec_id": r[0],
            "chain_id": chain_id,
            "task_id": r[1],
            "root_job_id": r[2],
            "parent_job_id": r[3],
            "kind": r[4],
            "params": _json_loads(r[5]) or {},
            "resolved_params": _json_loads(r[6]) if r[6] else None,
            "resolved": bool(r[7]),
            "status": r[8],
            "dedupe_key": r[9],
            "claim_id": r[10],
            "claimed_until": r[11],
            "dispatched_job_id": r[12],
        })
    return out

def claim_next_pending_spec(conn, chain_id: str, lease_seconds: int = 60) -> Optional[Dict[str, Any]]:
    """
    Atomically pick and lease the oldest pending spec that isn't already leased
    or whose lease has expired.
    """
    import uuid
    from datetime import timedelta
    
    now_dt = datetime.now(timezone.utc)
    now_iso = now_dt.isoformat()
    expires_iso = (now_dt + timedelta(seconds=lease_seconds)).isoformat()
    claim_id = str(uuid.uuid4())

    # Use a transaction for atomic Select-and-Update
    # SQLite's BEGIN IMMEDIATE prevents other threads/processes from starting a write txn
    conn.execute("BEGIN IMMEDIATE")
    try:
        # Find oldest candidate
        # Condition: pending AND (never claimed OR lease expired)
        row = conn.execute(
            """
            SELECT spec_id FROM chain_specs
            WHERE chain_id=? AND status='pending'
              AND (claimed_until IS NULL OR claimed_until < ?)
            ORDER BY created_at ASC
            LIMIT 1
            """,
            (chain_id, now_iso),
        ).fetchone()

        if not row:
            conn.execute("COMMIT")
            return None

        spec_id = row[0]

        # Update and claim
        conn.execute(
            """
            UPDATE chain_specs
            SET claim_id=?, claimed_until=?, updated_at=?
            WHERE spec_id=? AND status='pending'
              AND (claimed_until IS NULL OR claimed_until < ?)
            """,
            (claim_id, expires_iso, now_iso, spec_id, now_iso),
        )
        
        # Verify we actually updated a row (optimistic check)
        if conn.total_changes == 0:
            # Someone else was faster
            conn.execute("ROLLBACK")
            return None

        conn.execute("COMMIT")
        
        # Return the full spec
        # (Reloading from DB ensures we have the latest state)
        rows = conn.execute(
            """
            SELECT spec_id, task_id, root_job_id, parent_job_id, kind, params_json, resolved_params_json, resolved, status, dedupe_key, claim_id, claimed_until, dispatched_job_id
            FROM chain_specs WHERE spec_id=?
            """,
            (spec_id,),
        ).fetchone()
        
        return {
            "spec_id": rows[0],
            "chain_id": chain_id,
            "task_id": rows[1],
            "root_job_id": rows[2],
            "parent_job_id": rows[3],
            "kind": rows[4],
            "params": _json_loads(rows[5]) or {},
            "resolved_params": _json_loads(rows[6]) if rows[6] else None,
            "resolved": bool(rows[7]),
            "status": rows[8],
            "dedupe_key": rows[9],
            "claim_id": rows[10],
            "claimed_until": rows[11],
            "dispatched_job_id": rows[12],
        }
    except Exception:
        conn.execute("ROLLBACK")
        raise

def list_chains_needing_tick(conn, limit: int = 20) -> List[str]:
    """Find active chains that need processing, sorted by fairness."""
    rows = conn.execute(
        """
        SELECT chain_id FROM chain_context
        WHERE needs_tick=1 AND state='running'
        ORDER BY last_tick_at ASC NULLS FIRST
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [r[0] for r in rows]

def mark_chain_spec_dispatched(conn, chain_id: str, spec_id: str, job_id: str, claim_id: Optional[str] = None) -> None:
    """Mark spec as dispatched (idempotent with claim_id check)."""
    now = _now_iso()
    if claim_id:
        conn.execute(
            """
            UPDATE chain_specs
            SET status='dispatched', dispatched_job_id=?, updated_at=?
            WHERE chain_id=? AND spec_id=? AND claim_id=?
            """,
            (job_id, now, chain_id, spec_id, claim_id),
        )
    else:
        conn.execute(
            """
            UPDATE chain_specs
            SET status='dispatched', dispatched_job_id=?, updated_at=?
            WHERE chain_id=? AND spec_id=?
            """,
            (job_id, now, chain_id, spec_id),
        )
    conn.commit()

def update_chain_tick_time(conn, chain_id: str) -> None:
    """Update last_tick_at for fairness."""
    now = _now_iso()
    conn.execute(
        "UPDATE chain_context SET last_tick_at=?, updated_at=? WHERE chain_id=?",
        (now, now, chain_id),
    )
    conn.commit()

def mark_chain_spec_done(conn, chain_id: str, spec_id: str, ok: bool, info: Optional[Dict[str, Any]] = None) -> None:
    """Mark spec as done/failed."""
    now = _now_iso()
    conn.execute(
        """
        UPDATE chain_specs
        SET status=?, updated_at=?
        WHERE chain_id=? AND spec_id=?
        """,
        ("done" if ok else "failed", now, chain_id, spec_id),
    )
    conn.commit()
# ------------------------------------------------------------------------------
# HOSTS - CRUD (Track A2)
# ------------------------------------------------------------------------------

def get_host(host_id: str) -> Optional[Dict[str, Any]]:
    with get_db() as conn:
        r = conn.execute("SELECT * FROM hosts WHERE id = ?", (host_id,)).fetchone()
        if not r: return None
        return {
            "node_id": r['id'],
            "status": r['status'],
            "health": r['health'],
            "last_seen": r['last_seen'],
            "attestation": json.loads(r['attestation_json']),
            "metadata": json.loads(r['metadata_json'])
        }

def upsert_host(host_id: str, updates: Dict[str, Any]) -> None:
    """
    Update or insert host record. 
    'updates' can contain: status, health, last_seen, attestation, metadata.
    """
    existing = get_host(host_id)
    if not existing:
        existing = {
            "node_id": host_id,
            "status": "offline",
            "health": "GREEN",
            "last_seen": None,
            "attestation": {},
            "metadata": {}
        }
    
    # Apply updates
    if "status" in updates: existing["status"] = updates["status"]
    if "health" in updates: existing["health"] = updates["health"]
    if "last_seen" in updates: existing["last_seen"] = updates["last_seen"]
    if "attestation" in updates: existing["attestation"] = updates["attestation"]
    if "metadata" in updates: existing["metadata"] = updates["metadata"]

    with get_db() as conn:
        conn.execute("""
            INSERT OR REPLACE INTO hosts (id, status, health, last_seen, attestation_json, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            host_id, existing["status"], existing["health"], existing["last_seen"],
            json.dumps(existing["attestation"]), json.dumps(existing["metadata"])
        ))
        conn.commit()
