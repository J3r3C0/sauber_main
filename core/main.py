"""
Sheratan Core v2 – main.py
FastAPI Kernel for Missions → Tasks → Jobs → Worker Dispatch → LCP Followups
"""

from __future__ import annotations
from datetime import datetime
from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import List, Optional
import sys
import os
from pathlib import Path

# Force UTF-8 for Windows shell logging
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

# Add parent directory to sys.path so 'core' module can be imported
_parent_dir = Path(__file__).parent.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

from core import models
from core import storage
from core.webrelay_bridge import WebRelayBridge, WebRelaySettings
from core.lcp_actions import LCPActionInterpreter
from core.job_chain_manager import JobChainManager
from core.metrics_client import record_module_call, measured_call
from core.rate_limiter import RateLimiter
import json
import os
import psutil
import socket
import time

rate_limiter = RateLimiter()
CORE_START_TIME = time.time()

class Dispatcher:
    """Central dispatcher for Priority Queuing and Rate Limiting."""
    def __init__(self, bridge: WebRelayBridge, lcp: LCPActionInterpreter):
        self.bridge = bridge
        self.lcp = lcp
        self._running = False

    def start(self):
        self._running = True
        import threading
        threading.Thread(target=self._run_loop, daemon=True).start()
        print("[dispatcher] Central loops started.")

    def _run_loop(self):
        while self._running:
            try:
                # Periodic: Auto-activate planned missions (safety catch)
                missions = storage.list_missions()
                for m in missions:
                    # Robust check
                    m_status = getattr(m, 'status', None)
                    if m_status == "planned":
                        print(f"[dispatcher] ⚡ Auto-activating planned mission {m.id[:8]}")
                        m.status = "active"
                        storage.update_mission(m)
                    elif m_status is None:
                        # This should not happen if models are correct, let's log it
                        print(f"[dispatcher] ⚠️ Mission {m.id[:8]} missing status attribute. Type: {type(m)}")

                self._dispatch_step()
                self._sync_step()
            except Exception as e:
                print(f"[dispatcher] Error in loop: {e}")
            time.sleep(2)

    def _dispatch_step(self):
        # 1. Get Pending Jobs
        all_jobs = storage.list_jobs()
        pending = [j for j in all_jobs if j.status == "pending"]
        if not pending:
            return

        # 2. Idempotency / Deduplication Check
        completed_ids = {j.id for j in all_jobs if j.status == "completed"}
        completed_idempotency_keys = {j.idempotency_key for j in all_jobs if j.status == "completed" and j.idempotency_key}
        
        # 3. Filter Dependencies & Deduplicate
        ready = []
        for j in pending:
            # Deduplicate
            if j.idempotency_key and j.idempotency_key in completed_idempotency_keys:
                print(f"[dispatcher] ♻ Deduplicating job {j.id[:8]} (key={j.idempotency_key})")
                j.status = "completed"
                j.result = {"ok": True, "message": "idempotent_return", "deduplicated": True}
                j.updated_at = datetime.utcnow().isoformat() + "Z"
                storage.update_job(j)
                continue

            # Dependencies
            if not j.depends_on or all(dep_id in completed_ids for dep_id in j.depends_on):
                ready.append(j)
        
        if not ready:
            return

        # 4. Sort by Priority
        # priority_map: critical=0, high=1, normal=2
        priority_map = {"critical": 0, "high": 1, "normal": 2}
        ready.sort(key=lambda j: (priority_map.get(j.priority, 2), j.created_at))

        # 4. Filter Rate Limits
        # For now, we use a single 'system' source or per-mission-owner
        for job in ready:
            source = "default_user" # TODO: Get from mission/task
            if rate_limiter.check_limit(source):
                print(f"[dispatcher] 🚀 Dispatching job {job.id[:8]} (priority={job.priority})")
                job.status = "working"
                job.updated_at = datetime.utcnow().isoformat() + "Z"
                storage.update_job(job)
                self.bridge.enqueue_job(job.id)
            else:
                # Stop dispatching this batch if source is limited
                break

    def _sync_step(self):
        # Check all 'working' jobs for results
        working = [j for j in storage.list_jobs() if j.status in ["working", "running"]]
        for job in working:
            synced = self.bridge.try_sync_result(job.id)
            if synced:
                if synced.status == "failed":
                    # Retry logic handled here
                    max_retries = 3
                    if synced.retry_count < max_retries:
                        synced.retry_count += 1
                        synced.status = "pending"
                        synced.updated_at = datetime.utcnow().isoformat() + "Z"
                        storage.update_job(synced)
                        print(f"[dispatcher] ↺ Job {job.id[:8]} failed. Queued for retry ({synced.retry_count}/{max_retries})")
                        continue
                
                # Final result (success or max failure)
                print(f"[dispatcher] ✓ Job {job.id[:8]} finished with status: {synced.status}")
                self.lcp.handle_job_result(synced)



# --- PHASE 10.2: Chain Runner ---
from core.chain_runner import ChainRunner
chain_runner = ChainRunner()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Start Dispatcher (Legacy)
    dispatcher.start()
    # 2. Start Chain Runner (Phase 10.2)
    chain_runner.start()
    
    yield
    
    # Clean up
    dispatcher._running = False
    chain_runner.stop()

# ------------------------------------------------------------------------------
# APP INITIALISIERUNG
# ------------------------------------------------------------------------------

app = FastAPI(
    title="Sheratan Core v2",
    description="Mission/Task/Job orchestration kernel with WebRelay & LCP",
    version="2.0.0",
    lifespan=lifespan
)

# CORS erlauben – für HUD & externe Tools
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # später einschränken falls nötig
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files (HTML dashboards)
# Mount current directory to serve selfloop-dashboard.html etc.
_this_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=str(_this_dir), html=True), name="static")

# --- MESH ARBITRAGE EXCEPTION HANDLING ---
# Import PaymentRequiredError from the mesh package
try:
    from mesh.registry.client import PaymentRequiredError
    
    @app.exception_handler(PaymentRequiredError)
    async def payment_required_handler(request, exc: PaymentRequiredError):
        return JSONResponse(
            status_code=402,
            content=exc.to_json()
        )
except ImportError:
    # If mesh package is not available, we don't add the handler
    pass
# ------------------------------------------

# ------------------------------------------------------------------------------
# INITIALISIERUNG DER BRIDGE & LCP-ACTIONS
# ------------------------------------------------------------------------------

relay_settings = WebRelaySettings(
    relay_out_dir=storage.DATA_DIR.parent / "webrelay_out",
    relay_in_dir=storage.DATA_DIR.parent / "webrelay_in",
    session_prefix="core_v2"
)

bridge = WebRelayBridge(relay_settings)
lcp = LCPActionInterpreter(bridge=bridge)

# Phase 9: Initialize JobChainManager for LCP Job Chaining
from core.chain_index import ChainIndex
chain_index_path = storage.DATA_DIR / "chain_index.json"
chain_dir = storage.DATA_DIR / "chains"
chain_index = ChainIndex(str(chain_index_path))
chain_manager = JobChainManager(
    chain_dir=str(chain_dir),
    chain_index=chain_index,
    storage=storage,
    logger=None,  # Use print() for now
    agent_plan_kind="agent_plan",
)

# Dispatcher instantiation (BASIS FOR ALL AUTOMATION)
dispatcher = Dispatcher(bridge, lcp)
# dispatcher.start() # Now handled via lifespan


# ------------------------------------------------------------------------------
# MISSIONS – CRUD
# ------------------------------------------------------------------------------

@app.post("/api/missions", response_model=models.Mission)
def create_mission(mission_create: models.MissionCreate):
    mission = models.Mission.from_create(mission_create)
    # Ensure mission starts as active for immediate orchestration
    mission.status = "active"
    storage.create_mission(mission)
    
    # Initialize mission documentation files
    try:
        mission_dir = storage.DATA_DIR / "missions"
        mission_dir.mkdir(parents=True, exist_ok=True)
        
        plan_file = mission_dir / f"{mission.id}_plan.md"
        progress_file = mission_dir / f"{mission.id}_progress.md"
        
        # Initial plan content
        plan_content = f"# Mission Plan: {mission.title}\n\n## Objective\n{mission.description}\n\n## Status\nActive\n"
        plan_file.write_text(plan_content, encoding="utf-8")
        
        # Initial progress content
        progress_content = f"# Mission Progress: {mission.title}\n\n## Log\n[Init] Mission created at {mission.created_at}\n"
        progress_file.write_text(progress_content, encoding="utf-8")
        
        print(f"[api] Created mission files and ACTIVATED mission {mission.id[:8]}")
    except Exception as e:
        print(f"[api] Warning: Could not create mission files: {e}")

    return mission


@app.get("/api/missions", response_model=List[models.Mission])
def list_missions():
    return storage.list_missions()


@app.get("/api/missions/{mission_id}", response_model=models.Mission)
def get_mission(mission_id: str):
    m = storage.get_mission(mission_id)
    if m is None:
        raise HTTPException(404, "Mission not found")
    return m


@app.put("/api/missions/{mission_id}", response_model=models.Mission)
def update_mission(mission_id: str, mission: models.Mission):
    m = storage.get_mission(mission_id)
    if m is None:
        raise HTTPException(404, "Mission not found")
    
    # Ensure ID consistency
    mission.id = mission_id
    storage.update_mission(mission)
    return mission


@app.delete("/api/missions/{mission_id}")
def delete_mission(mission_id: str):
    """Delete a mission and all its related tasks and jobs."""
    success = storage.delete_mission(mission_id)
    if not success:
        raise HTTPException(404, "Mission not found")
    return {"ok": True, "deleted": mission_id}


# ------------------------------------------------------------------------------
# TASKS – CRUD
# ------------------------------------------------------------------------------

@app.post("/api/missions/{mission_id}/tasks", response_model=models.Task)
def create_task_for_mission(mission_id: str, task_create: models.TaskCreate):
    m = storage.get_mission(mission_id)
    if m is None:
        raise HTTPException(404, "Mission not found")

    task = models.Task.from_create(mission_id, task_create)
    storage.create_task(task)
    return task


@app.get("/api/tasks", response_model=List[models.Task])
def list_tasks():
    return storage.list_tasks()


@app.get("/api/tasks/{task_id}", response_model=models.Task)
def get_task(task_id: str):
    t = storage.get_task(task_id)
    if t is None:
        raise HTTPException(404, "Task not found")
    return t


# ------------------------------------------------------------------------------
# JOBS – CRUD & DISPATCH
# ------------------------------------------------------------------------------

@app.post("/api/tasks/{task_id}/jobs", response_model=models.Job)
def create_job_for_task(task_id: str, job_create: models.JobCreate):
    t = storage.get_task(task_id)
    if t is None:
        raise HTTPException(404, "Task not found")
    
    job = models.Job.from_create(task_id, job_create)
    storage.create_job(job)
    return job


@app.get("/api/jobs", response_model=List[models.Job])
def list_jobs():
    return storage.list_jobs()


@app.get("/api/jobs/{job_id}", response_model=models.Job)
def get_job(job_id: str):
    j = storage.get_job(job_id)
    if j is None:
        raise HTTPException(404, "Job not found")
    return j


@app.put("/api/jobs/{job_id}", response_model=models.Job)
def update_job(job_id: str, job: models.Job):
    j = storage.get_job(job_id)
    if j is None:
        raise HTTPException(404, "Job not found")
    
    # Ensure ID consistency
    job.id = job_id
    storage.update_job(job)
    return job


# ------------------------------------------------------------------------------
# JOB → WORKER DISPATCH
# ------------------------------------------------------------------------------

@app.post("/api/jobs/{job_id}/dispatch")
def dispatch_job(job_id: str):
    """
    Manually triggers dispatch (legacy/forced).
    Now mostly handled by central Dispatcher.
    """
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    # Just set status to pending if it's not already
    if job.status != "working":
        job.status = "pending"
        storage.update_job(job)
    
    return {"status": "queued", "job_id": job_id}


# ------------------------------------------------------------------------------
# JOB → RESULT SYNC + LCP FOLLOWUP
# ------------------------------------------------------------------------------

@app.post("/api/jobs/{job_id}/sync", response_model=models.Job)
def sync_job(job_id: str):
    """
    1. Liest Worker-Result
    2. Speichert es am Job
    3. Führt LCPActionInterpreter aus (→ Follow-Up Jobs)
    4. Gibt aktualisierten Job zurück
    """
    # 1) Worker-Result einlesen
    job = bridge.try_sync_result(job_id)
    if job is None:
        # Worker hat noch nichts geliefert
        raise HTTPException(404, "Result not found")

    # 2) Worker-Latenz ermitteln (Job-Erstellung → Result Sync)
    worker_latency_ms = 0.0
    try:
        # job.created_at ist bereits ISO-String, z.B. "2025-12-08T12:34:56.123456Z"
        created = datetime.fromisoformat(job.created_at.replace("Z", ""))
        now = datetime.utcnow()
        worker_latency_ms = (now - created).total_seconds() * 1000.0
    except Exception:
        # Wenn irgendwas schiefgeht, ist das nur Monitoring – Core läuft weiter
        pass

    # Event: Worker → Core
    # This is now non-blocking because record_module_call uses a thread.
    record_module_call(
        source="webrelay_worker",
        target="core_v2.api.sync_job",
        duration_ms=worker_latency_ms,
        status="ok" if job.status != "failed" else "error",
        correlation_id=f"job:{job_id}",
    )

    # 3) Phase 10.1: Chain Context + Specs Handling (Thin Sync)
    if job.result and isinstance(job.result, dict):
        from core.lcp_actions import parse_lcp
        from core.context_updaters import update_context_from_job_result
        
        # Try to parse LCP envelope
        followup, final = parse_lcp(job.result, default_chain_id=job_id)
        
        # Determine chain_id
        task = storage.get_task(job.task_id)
        chain_id = task.params.get("chain_id") or job_id if task else job_id

        # Update chain context from job result (e.g. store file_list after walk_tree)
        with get_db() as conn:
            # Ensure context exists
            storage.ensure_chain_context(conn, chain_id, job.task_id)
            
            # Update artifacts (file_list, file_blobs, etc)
            artifact_key = update_context_from_job_result(
                conn,
                chain_id=chain_id,
                job_kind=job.payload.get("kind") if isinstance(job.payload, dict) else "unknown",
                job_id=job_id,
                result=job.result,
                set_chain_artifact_fn=storage.set_chain_artifact
            )
            if artifact_key:
                print(f"[sync_job] Updated artifact '{artifact_key}' for chain {chain_id[:12]}")

        if followup or final:
            print(f"[sync_job] LCP envelope detected for job {job_id[:12]}...")
            
            # Ensure chain exists in manager (creates file if needed)
            chain_manager.ensure_chain(chain_id=chain_id, root_job_id=job_id)
            
            if followup:
                # Register follow-up SPECS (not jobs!)
                print(f"[sync_job] Registering {len(followup.jobs)} followup specs...")
                chain_manager.register_followup_specs(
                    chain_id=chain_id,
                    task_id=job.task_id,
                    root_job_id=job_id,
                    parent_llm_job_id=job_id,
                    job_specs=followup.jobs
                )
                
                # Note: dispatch_next_llm_step is REMOVED here. 
                # The ChainRunner (Phase 10.2) will pick up the 'needs_tick' flag.
                
            elif final:
                # Close chain with final answer
                print(f"[sync_job] Closing chain {chain_id[:12]} with final answer...")
                chain_manager.close_chain(chain_id=chain_id, final_answer=final.answer)
        else:
            # No LCP envelope - run old LCP handler for legacy support
            with measured_call(
                source="core_v2.api.sync_job",
                target="core_v2.lcp_actions.handle_job_result",
                correlation_id=f"job:{job_id}",
            ):
                lcp.handle_job_result(job)

    # Job ist bereits von bridge.try_sync_result() aktualisiert
    return job



# ------------------------------------------------------------------------------
# MESH & LEDGER – MONITORING
# ------------------------------------------------------------------------------

@app.get("/api/mesh/workers")
def list_mesh_workers():
    """Returns all workers registered in the Mesh Registry. Reloads from disk."""
    try:
        if not hasattr(bridge, 'registry') or not bridge.registry:
            return []
        
        # Reload from disk to see workers that registered after Core started
        bridge.registry.load()
        
        return [w.model_dump() for w in bridge.registry.workers.values()]
    except Exception as e:
        print(f"[api] Error listing workers: {e}")
        return []

@app.get("/api/mesh/ledger/{user_id}")
def get_user_balance(user_id: str):
    """Returns the balance and recent transfers for a user."""
    try:
        if not hasattr(bridge, 'ledger') or not bridge.ledger:
            return {"balance": 0, "transfers": []}
            
        client = bridge.ledger
        balance = client.get_balance(user_id)
        # Load transfers from the store directly for monitoring
        transfers = []
        if hasattr(client, 'store') and client.store:
            raw_transfers = getattr(client.store, 'transfers', [])
            transfers = [t for t in raw_transfers if t.get("from") == user_id or t.get("to") == user_id]
            
        return {
            "user_id": user_id,
            "balance": balance,
            "transfers": transfers[-20:] # Last 20
        }
    except Exception as e:
        print(f"[api] Error getting balance for {user_id}: {e}")
        return {"balance": 0, "transfers": [], "error": str(e)}

@app.post("/api/hosts/heartbeat")
async def host_heartbeat(payload: dict):
    """
    Receives status from hosts and updates the registry/mesh state.
    """
    host_id = payload.get("host_id")
    status = payload.get("status")
    print(f"[heartbeat] Received update from {host_id}: {status}")
    
    # Update active status in broker's discovery file (simplified integration)
    try:
        hosts_file = storage.DATA_DIR.parent / "mesh" / "offgrid" / "discovery" / "mesh_hosts.json"
        if hosts_file.exists():
            data = json.loads(hosts_file.read_text(encoding="utf-8"))
            for url in data:
                if data[url].get("node_id") == host_id or host_id in url:
                    data[url]["active"] = (status == "online")
                    data[url]["last_seen"] = datetime.utcnow().isoformat() + "Z"
            hosts_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[heartbeat] Failed to update host status: {e}")
        
    return {"ok": True}


# ------------------------------------------------------------------------------
# PROJECTS & FILES – EXPLORER
# ------------------------------------------------------------------------------

SHERATAN_ROOT = storage.config.BASE_DIR

@app.get("/api/projects")
def list_projects():
    """Lists subdirectories in the Sheratan root as projects."""
    projects = []
    try:
        from datetime import datetime
        for entry in os.scandir(SHERATAN_ROOT):
            if entry.is_dir() and not entry.name.startswith(('.', '_', 'Z_')):
                stats = entry.stat()
                projects.append({
                    "id": entry.name,
                    "name": entry.name.replace('_', ' ').title(),
                    "path": str(entry.path),
                    "status": "active",
                    "lastAccess": datetime.fromtimestamp(stats.st_atime).isoformat() + "Z",
                    "fileCount": 0
                })
    except Exception as e:
        print(f"[api] Error listing projects: {e}")
    return projects

@app.get("/api/projects/{project_id}/files", response_model=List[dict])
def list_project_files(project_id: str):
    """Returns a simple file tree for a project."""
    project_path = SHERATAN_ROOT / project_id
    if not project_path.exists() or not project_path.is_dir():
        raise HTTPException(404, "Project not found")
    
    def get_tree(path: Path, depth=0):
        if depth > 2: # Limit depth
            return []
        nodes = []
        try:
            for entry in os.scandir(path):
                if entry.name.startswith(('.', 'node_modules', '__pycache__', '.git')):
                    continue
                node = {
                    "name": entry.name,
                    "path": str(entry.path),
                    "type": "directory" if entry.is_dir() else "file"
                }
                if entry.is_dir():
                    node["children"] = get_tree(Path(entry.path), depth + 1)
                nodes.append(node)
        except Exception:
            pass
        return nodes

    return get_tree(project_path)


# ------------------------------------------------------------------------------
# SYSTEM HEALTH & METRICS
# ------------------------------------------------------------------------------

@app.get("/api/system/metrics")
def get_system_metrics():
    """Returns real CPU, RAM and Queue length metrics."""
    try:
        cpu = psutil.cpu_percent(interval=None)
        memory = psutil.virtual_memory().percent
        all_jobs = storage.list_jobs()
        queue_len = len([j for j in all_jobs if j.status in ["pending", "running", "working", "queued"]])
        
        # Simple error rate: failed jobs / total jobs (last 100)
        recent_jobs = all_jobs[-100:]
        failed = len([j for j in recent_jobs if j.status == "failed" or j.status == "error"])
        error_rate = (failed / len(recent_jobs) * 100) if recent_jobs else 0

        return {
            "cpu": cpu,
            "memory": memory,
            "queueLength": queue_len,
            "errorRate": round(error_rate, 2),
            "uptime": int(time.time() - psutil.boot_time())
        }
    except Exception as e:
        print(f"[api] Error fetching metrics: {e}")
        return {"cpu": 0, "memory": 0, "queueLength": 0, "errorRate": 0}

@app.post("/metrics/module-calls")
def post_module_metrics(payload: dict):
    """Telemetry endpoint for internal module calls (fire-and-forget)."""
    # For now just log to terminal if needed, or just return 200
    # print(f"[metrics] {payload.get('source')} -> {payload.get('target')} ({payload.get('duration_ms')}ms)")
    return {"ok": True}

import asyncio

@app.get("/api/system/health")
async def get_system_health():
    """Checks the status of key sheratan services by checking ports."""
    services = [
        {"name": "Core API", "port": 8001, "expected": "up"},
        {"name": "WebRelay", "port": 3000, "expected": "up"},
        {"name": "Broker", "port": 9000, "expected": "up"},
        {"name": "Host-A", "port": 8081, "expected": "up"},
        {"name": "Dashboard", "port": 3001, "expected": "up"}
    ]
    
    results = []
    now_ts = time.time()
    for s in services:
        status = "down"
        # Avoid self-ping deadlock (uvicorn single worker)
        if s['port'] == 8001:
            status = "active"
        else:
            # Try 127.0.0.1 first (standard for Windows local binding)
            targets = ['127.0.0.1', 'localhost']
            for target in targets:
                try:
                    conn = asyncio.open_connection(target, s['port'])
                    _, writer = await asyncio.wait_for(conn, timeout=1.0)
                    writer.close()
                    await writer.wait_closed()
                    status = "active"
                    break
                except:
                    pass
        
        # Calculate uptime string
        uptime_str = "N/A"
        if status == "active":
            if s['port'] == 8001:
                diff = int(now_ts - CORE_START_TIME)
                hours, rem = divmod(diff, 3600)
                minutes, seconds = divmod(rem, 60)
                uptime_str = f"{hours}h {minutes}m {seconds}s"
            else:
                uptime_str = "online"

        results.append({
            "id": s['name'].lower().replace(" ", "-"),
            "name": s['name'],
            "status": status,
            "port": s['port'],
            "uptime": uptime_str,
            "lastCheck": datetime.utcnow().isoformat() + "Z",
            "type": "core" if s['port'] == 8001 else ("relay" if s['port'] == 3000 else "engine"),
            "dependencies": ["core-api"] if s['port'] != 8001 else []
        })
    return results


# ------------------------------------------------------------------------------
# MISC – HEALTH ENDPOINT
# ------------------------------------------------------------------------------

@app.get("/api/status")
def status():
    return {"status": "ok", "missions": len(storage.list_missions())}


# ------------------------------------------------------------------------------
# ROOT
# ------------------------------------------------------------------------------

@app.get("/")
def root():
    return JSONResponse({"sheratan_core_v2": "running"})


# ------------------------------------------------------------------------------
# QUICK START – MISSION TEMPLATES
# ------------------------------------------------------------------------------

@app.post("/api/missions/standard-code-analysis")
def create_standard_code_analysis():
    """Boss Directive 4.1: One-click playground mission directly in Core."""
    title = "System verstehen"
    description = (
        "Analysiere die Scripts des aktuellen Systems, erstelle ein Lagebild "
        "und mache dir Notizen in der Mission-Plan Datei."
    )

    # 1. Create Mission (using model)
    mission_create = models.MissionCreate(
        title=title,
        description=description,
        metadata={"created_by": "dashboard_quickstart", "max_iterations": 100}
    )
    mission = models.Mission.from_create(mission_create)
    storage.create_mission(mission)

    # 2. Create agent_plan Task
    task_create = models.TaskCreate(
        name="Initial codebase analysis",
        description="Let the agent inspect the codebase and plan followup jobs.",
        kind="agent_plan",
        params={
            "user_prompt": f"Analysiere das Repository unter {SHERATAN_ROOT} und erstelle ein Lagebild. Beachte: Die Core-Logik liegt in core/.",
            "project_root": str(SHERATAN_ROOT)
        }
    )
    task = models.Task.from_create(mission.id, task_create)
    storage.create_task(task)

    # 3. Create Job (properly structured for worker)
    job_create = models.JobCreate(
        payload={
            "task": {
                "kind": "agent_plan",
                "params": task_create.params
            },
            "params": {
                **task_create.params,
                "iteration": 1
            }
        }
    )
    job = models.Job.from_create(task.id, job_create)
    storage.create_job(job)

    # 4. Auto-Queue (Dispatcher takes over)
    print(f"[api] QuickStart mission created: {mission.id[:8]}. Job {job.id[:8]} queued.")
    
    return {
        "mission": {"id": mission.id, "title": mission.title},
        "task": {"id": task.id, "name": task.name},
        "job": {"id": job.id}
    }


# ------------------------------------------------------------------------------
# MESH WORKER REGISTRATION
# ------------------------------------------------------------------------------

@app.post("/api/mesh/workers/register")
def register_worker(worker_data: dict):
    """Register a worker in the Mesh Registry."""
    try:
        from mesh.registry.mesh_registry import WorkerRegistry, WorkerInfo, WorkerCapability
        from pathlib import Path
        
        registry_file = Path(__file__).parent.parent / "mesh" / "registry" / "workers.json"
        registry = WorkerRegistry(registry_file)
        
        # Convert capabilities dict to WorkerCapability objects
        capabilities = [
            WorkerCapability(kind=cap['kind'], cost=cap['cost'])
            for cap in worker_data.get('capabilities', [])
        ]
        
        worker_info = WorkerInfo(
            worker_id=worker_data['worker_id'],
            capabilities=capabilities,
            status=worker_data.get('status', 'online'),
            endpoint=worker_data.get('endpoint'),
            meta=worker_data.get('meta', {})
        )
        
        registry.register(worker_info)
        
        print(f"[mesh] ✓ Registered worker: {worker_data['worker_id']} with {len(capabilities)} capabilities")
        
        return {
            "ok": True,
            "worker_id": worker_data['worker_id'],
            "message": f"Worker registered successfully"
        }
    except Exception as e:
        print(f"[mesh] ✗ Registration failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/mesh/workers")
def list_workers():
    """List all registered workers."""
    try:
        from mesh.registry.mesh_registry import WorkerRegistry
        from pathlib import Path
        
        registry_file = Path(__file__).parent.parent / "mesh" / "registry" / "workers.json"
        registry = WorkerRegistry(registry_file)
        registry.load()
        
        workers = []
        for worker_id, worker_info in registry.workers.items():
            workers.append({
                "worker_id": worker_id,
                "capabilities": [{"kind": c.kind, "cost": c.cost} for c in worker_info.capabilities],
                "status": worker_info.status,
                "last_seen": worker_info.last_seen,
                "stats": {
                    "n": worker_info.stats.n,
                    "success_ema": worker_info.stats.success_ema,
                    "latency_ms_ema": worker_info.stats.latency_ms_ema,
                    "consecutive_failures": worker_info.stats.consecutive_failures,
                    "is_offline": worker_info.stats.is_offline,
                    "cooldown_until": worker_info.stats.cooldown_until,
                    "active_jobs": worker_info.stats.active_jobs
                },
                "meta": worker_info.meta
            })
        
        return workers
    except Exception as e:
        print(f"[mesh] Error listing workers: {e}")
        return []


if __name__ == "__main__":
    import uvicorn
    # Start on 8001 as specified in DASHBOARDS.md
    print("--- Sheratan Core v2 starting on http://localhost:8001 ---")
    uvicorn.run(app, host="0.0.0.0", port=8001)
