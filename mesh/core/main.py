"""
Sheratan Core v2 – main.py
FastAPI Kernel for Missions -> Tasks -> Jobs -> Worker Dispatch -> LCP Followups
"""

from __future__ import annotations
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from typing import List, Optional
import json
import asyncio
import uuid
import os
from dotenv import load_dotenv

# Load .env from v_core (which is one level up from this file's parent)
_this_file_dir = Path(__file__).parent
load_dotenv(_this_file_dir / ".." / ".env")

from . import models
from . import storage
from .webrelay_bridge import WebRelayBridge, WebRelaySettings
from .offgrid_bridge import OffgridBridge, OffgridConfig
from . import llm_analyzer
from .lcp_actions import LCPActionInterpreter
from .metrics_client import record_module_call, measured_call
from .event_logger import RealityLogger

# v1 Lock enforcement (fail-closed by default)
from .bootstrap_lockcheck import enforce_lock_or_raise

from .dispatcher import run_dispatch
# Auditor moved to separate process (see start_auditor.ps1)


from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Lock enforcement
    # If lock/contract/codebook mismatch -> raise, server fails to start.
    enforce_lock_or_raise()
    
    # 2. Start mesh status monitor (background task)
    from . import mesh_monitor
    mesh_monitor.start_mesh_monitor()

    # 3. Start LLM analyzer for auto-documentation
    await llm_analyzer.start_llm_analyzer()

    # 4. Start Smart Heartbeat (SYSTEM_TICK)
    asyncio.create_task(heartbeat_loop())
    
    # 5. Start Input Watcher (Auto-Dispatch)
    asyncio.create_task(input_watcher_loop())
    
    yield

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

# ------------------------------------------------------------------------------
# INITIALISIERUNG DER BRIDGE & LCP-ACTIONS
# ------------------------------------------------------------------------------

relay_settings = WebRelaySettings(
    relay_out_dir=storage.DATA_DIR.parent / "runtime" / "transport" / "webrelay_out",
    relay_in_dir=storage.DATA_DIR.parent / "runtime" / "transport" / "webrelay_in",
    session_prefix="core_v2"
)

offgrid_settings = OffgridConfig(
    broker_url="http://127.0.0.1:9000",
    auth_key="shared-secret"
)

bridge = WebRelayBridge(relay_settings)
offgrid = OffgridBridge(offgrid_settings)
lcp = LCPActionInterpreter(bridge=bridge)


async def heartbeat_loop():
    """Observational heartbeat that logs system state to the Reality Ledger."""
    logger = RealityLogger("core")
    print("[core] Starting Smart Heartbeat...")
    
    # Paths for queue depth monitoring
    runtime = Path(__file__).parent.parent.parent / "runtime"
    queues = {
        "narrative": runtime / "narrative",
        "proofed": runtime / "proofed",
        "input": runtime / "input",
        "quarantine": runtime / "quarantine"
    }

    while True:
        try:
            # 1. Calculate Queue Depths
            depths = {}
            for name, path in queues.items():
                if path.exists():
                    # Count only json files (ignoring .processed, .processing etc)
                    depths[name] = len(list(path.glob("*.json")))
                else:
                    depths[name] = 0

            # 2. Components Seen Last 5m (from ledger tail)
            seen = set()
            try:
                ledger_path = runtime / "output" / "ledger.jsonl"
                if ledger_path.exists():
                    with open(ledger_path, "r", encoding="utf-8") as f:
                        lines = f.readlines()[-100:] # Last 100 events
                        now = datetime.now(timezone.utc)
                        for line in reversed(lines):
                            try:
                                entry = json.loads(line)
                                # Reality Ledger uses Zulu (Z) format from event_logger.py
                                ts_str = entry["ts"].replace("Z", "+00:00")
                                ts = datetime.fromisoformat(ts_str)
                                
                                if (now - ts).total_seconds() < 300: # 5 minutes
                                    seen.add(entry["actor"])
                            except:
                                continue
            except Exception as e:
                print(f"[core] Heartbeat scan error: {e}")

            # 3. Log SYSTEM_TICK
            logger.log(
                event="SYSTEM_TICK",
                job_id=None,
                zone="output",
                meta={
                    "components_seen_last_5m": list(seen),
                    "queue_depths": depths
                }
            )
            
        except Exception as e:
            print(f"[core] Heartbeat error: {e}")
            
        await asyncio.sleep(60)



# ------------------------------------------------------------------------------
# HEALTH CHECK
# ------------------------------------------------------------------------------

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring."""
    return {
        "status": "healthy",
        "service": "sheratan_core_v2",
        "version": "2.0",
        "components": {
            "auditor_relay": "running",
            "mesh_monitor": "running",
            "llm_analyzer": "running"
        }
    }


@app.get("/api/status")
async def api_status():
    """Legacy status endpoint (alias for /health)."""
    return await health_check()


# ------------------------------------------------------------------------------
# MISSIONS – CRUD
# ------------------------------------------------------------------------------

@app.post("/api/missions", response_model=models.Mission)
def create_mission(payload: models.MissionCreate):
    mission = models.Mission.from_create(payload)
    storage.create_mission(mission)
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
def create_task_for_mission(mission_id: str, payload: models.TaskCreate):
    m = storage.get_mission(mission_id)
    if m is None:
        raise HTTPException(404, "Mission not found")

    task = models.Task.from_create(mission_id, payload)
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
def create_job_for_task(task_id: str, payload: models.JobCreate):
    t = storage.get_task(task_id)
    if t is None:
        raise HTTPException(404, "Task not found")
    
    job = models.Job.from_create(task_id, payload)
    storage.create_job(job)
    return job


@app.get("/api/jobs", response_model=List[models.Job])
def list_jobs():
    """
    List all jobs (deduplicated).
    
    Uses "Latest Wins" strategy for research jobs:
    - Only returns latest version of each semantic job_id
    - Prevents duplicate execution on reissue
    """
    return storage.list_jobs_deduplicated()


@app.get("/api/jobs/{job_id}", response_model=models.Job)
def get_job(job_id: str):
    j = storage.get_job(job_id)
    if j is None:
        raise HTTPException(404, "Job not found")
    return j


@app.delete("/api/jobs/{job_id}")
def delete_job(job_id: str):
    """Delete a specific job by ID."""
    success = storage.delete_job(job_id)
    if not success:
        raise HTTPException(404, "Job not found")
    return {"ok": True, "deleted": job_id}


# ------------------------------------------------------------------------------
# JOB -> WORKER DISPATCH
# ------------------------------------------------------------------------------

@app.post("/api/jobs/{job_id}/dispatch")
def dispatch_job(job_id: str):
    """
    Capability-based Job Router (The Scheduler).
    Determines if a job should go to WebRelay (Brain) or Offgrid (Body).
    """
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    task = storage.get_task(job.task_id)
    if not task:
        raise HTTPException(404, "Task not found")

    # Policy Decision: Brain (LLM/Browser) vs Body (OS/Compute)
    brain_kinds = ["agent_plan", "llm_call", "discovery", "sheratan_selfloop", "self_loop", "webrelay"]
    route_to_offgrid = task.kind not in brain_kinds

    # Correlation ID for end-to-end tracing (Phase 4)
    correlation_id = f"req-{uuid.uuid4().hex[:8]}"

    if route_to_offgrid:
        # ----------------------------------------------------------------------
        # BODY ROUTE: Offgrid Mesh (Auction)
        # ----------------------------------------------------------------------
        print(f"[scheduler] Routing '{task.kind}' to OFFGRID Data-Plane (req_id={correlation_id})")
        storage.create_job_event(models.JobEvent.create(
            job_id, "AUCTION_STARTED", metadata={"req_id": correlation_id}
        ))
        
        import threading
        def run_auction():
            try:
                # Synchronous auction & execution polling
                updated_job = offgrid.dispatch_job(job_id, correlation_id=correlation_id)
                if updated_job and updated_job.status == "completed":
                    print(f"[scheduler] ✓ Offgrid job {job_id[:8]} completed")
                    lcp.handle_job_result(updated_job)
            except Exception as e:
                print(f"[scheduler] [FAIL] Offgrid auction failed for {job_id[:8]}: {e}")
                storage.create_job_event(models.JobEvent.create(job_id, "FAILED", metadata={"error": str(e)}))

        thread = threading.Thread(target=run_auction, daemon=True)
        thread.start()
        
        return {"ok": True, "route": "offgrid", "status": "auction_started"}

    else:
        # ----------------------------------------------------------------------
        # BRAIN ROUTE: WebRelay (ChatGPT)
        # ----------------------------------------------------------------------
        print(f"[scheduler] Routing '{task.kind}' to WEBRELAY Data-Plane")
        try:
            bridge.enqueue_job(job_id)
            storage.create_job_event(models.JobEvent.create(job_id, "DISPATCHED", metadata={"target": "webrelay"}))
        except Exception as e:
            raise HTTPException(500, f"WebRelay dispatch failed: {e}")

        # Start background polling for result
        import threading
        def poll_and_sync():
            import time
            max_attempts = 120  # Poll longer for LLM calls
            for i in range(max_attempts):
                time.sleep(1)
                try:
                    synced_job = bridge.try_sync_result(job_id)
                    if synced_job and synced_job.result:
                        print(f"[auto-sync] ✓ Result for {job_id[:8]} after {i+1}s")
                        lcp.handle_job_result(synced_job)
                        break
                except Exception:
                    pass

        thread = threading.Thread(target=poll_and_sync, daemon=True)
        thread.start()
        
        return {"ok": True, "route": "webrelay", "status": "dispatched"}


@app.get("/dispatch/job/{job_id}")
async def get_job_status(job_id: str):
    """
    Returns simplified status. For full details use /narrative/{job_id}
    """
    # (Existing logic or simple check)
    return {"job_id": job_id, "status": "See /narrative for details"}

@app.get("/dispatch/narrative/{job_id}")
async def get_job_narrative(job_id: str):
    """
    Returns the SystemNarrative (Unified View) for a job.
    """
    from .dispatcher import synthesize_narrative
    return synthesize_narrative(job_id)

@app.post("/dispatch/job")
def dispatch_job_proposal(job: Dict[str, Any] = Body(...)):
    """
    Accepts a job proposal (NON-EXEC), runs gates, and only emits to runtime/input on PASS.
    """
    try:
        # Using Path(".") as root, which is usually C:/projectroot when running core
        result = run_dispatch(job, project_root=Path("."))
        return result
    except Exception as e:
        # Fail-closed: core should not proceed silently
        raise HTTPException(status_code=500, detail=f"dispatch failed: {e}")


# Wire LCP Interpreter to Unified Dispatcher
lcp.dispatch_fn = dispatch_job

# Start background tasks
# start_auditor_relay() -> Moved to startup event for event loop safety


# ------------------------------------------------------------------------------
# JOB -> RESULT SYNC + LCP FOLLOWUP
# ------------------------------------------------------------------------------

@app.post("/api/jobs/{job_id}/sync", response_model=models.Job)
def sync_job(job_id: str):
    """
    1. Liest Worker-Result
    2. Speichert es am Job
    3. Führt LCPActionInterpreter aus (-> Follow-Up Jobs)
    4. Gibt aktualisierten Job zurück
    """
    # 1) Worker-Result einlesen
    job = bridge.try_sync_result(job_id)
    if job is None:
        # Worker hat noch nichts geliefert
        raise HTTPException(404, "Result not found")

    # 2) Worker-Latenz ermitteln (Job-Erstellung -> Result Sync)
    worker_latency_ms = 0.0
    try:
        # job.created_at ist bereits ISO-String, z.B. "2025-12-08T12:34:56.123456Z"
        created = datetime.fromisoformat(job.created_at.replace("Z", ""))
        now = datetime.utcnow()
        worker_latency_ms = (now - created).total_seconds() * 1000.0
    except Exception:
        # Wenn irgendwas schiefgeht, ist das nur Monitoring – Core läuft weiter
        pass

    # Event: Worker -> Core
    record_module_call(
        source="webrelay_worker",
        target="core_v2.api.sync_job",
        duration_ms=worker_latency_ms,
        status="ok" if job.status != "failed" else "error",
        correlation_id=f"job:{job_id}",
    )

    # 3) LCP-Followups erzeugen (kostet ggf. CPU)
    with measured_call(
        source="core_v2.api.sync_job",
        target="core_v2.lcp_actions.handle_job_result",
        correlation_id=f"job:{job_id}",
    ):
        followups = lcp.handle_job_result(job)

    # Job ist bereits von bridge.try_sync_result() aktualisiert
    return job


# ------------------------------------------------------------------------------
# MISC – HEALTH ENDPOINT
# ------------------------------------------------------------------------------

@app.get("/api/status")
def status():
    return {"status": "ok", "missions": len(storage.list_missions())}


@app.get("/api/health")
def health():
    """Health check endpoint (alias for /api/status)"""
    return {"status": "ok", "missions": len(storage.list_missions())}


# ------------------------------------------------------------------------------
# SELF-LOOP API ENDPOINTS
# ------------------------------------------------------------------------------

@app.post("/api/selfloop/create")
def create_selfloop_mission(
    title: str,
    goal: str,
    initial_context: str = "",
    max_iterations: int = 10,
    constraints: list = None
):
    """Create a new Self-Loop mission."""
    from .selfloop_prompt_builder import build_selfloop_job_payload
    
    mission_create = models.MissionCreate(
        title=title,
        description=f"Self-Loop: {goal}",
        metadata={"type": "selfloop", "max_iterations": max_iterations}
    )
    mission = models.Mission.from_create(mission_create)
    storage.create_mission(mission)
    
    task_create = models.TaskCreate(
        name="selfloop_iteration",
        description="Self-Loop collaborative co-thinking",
        kind="selfloop",
        params={}
    )
    task = models.Task.from_create(mission.id, task_create)
    storage.create_task(task)
    
    job_payload = build_selfloop_job_payload(
        goal=goal,
        initial_context=initial_context or f"Mission: {title}",
        max_iterations=max_iterations,
        constraints=constraints
    )
    
    job_create = models.JobCreate(payload=job_payload)
    job = models.Job.from_create(task.id, job_create)
    storage.create_job(job)
    
    bridge.enqueue_job(job.id)
    
    return {
        "ok": True,
        "mission": mission.to_dict(),
        "task": task.to_dict(),
        "job": job.to_dict()
    }


@app.get("/api/selfloop/{mission_id}/status")
def get_selfloop_status(mission_id: str):
    """Get Self-Loop mission status with iteration history."""
    mission = storage.get_mission(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    
    tasks = storage.list_tasks(mission_id)
    jobs = []
    for task in tasks:
        jobs.extend(storage.list_jobs(task.id))
    
    latest_job = jobs[-1] if jobs else None
    loop_state = None
    if latest_job and latest_job.payload.get("job_type") == "sheratan_selfloop":
        loop_state = latest_job.payload.get("loop_state", {})
    
    return {
        "ok": True,
        "mission": mission.to_dict(),
        "tasks": [t.to_dict() for t in tasks],
        "jobs": [j.to_dict() for j in jobs],
        "loop_state": loop_state,
        "iteration": loop_state.get("iteration", 1) if loop_state else 1,
        "total_jobs": len(jobs)
    }


# ------------------------------------------------------------------------------
# ROOT
# ------------------------------------------------------------------------------

@app.get("/")
def root():
    return JSONResponse({"sheratan_core_v2": "running"})


# ------------------------------------------------------------------------------
# INPUT WATCHER (Auto-Dispatch)
# ------------------------------------------------------------------------------

async def input_watcher_loop():
    """
    Watches runtime/input for approved jobs and auto-dispatches them.
    This completes the pipeline: narrative -> gates -> input -> broker -> execution
    """
    print("[input_watcher] Starting Input Watcher...")
    
    input_dir = Path(__file__).parent.parent.parent / "runtime" / "input"
    input_dir.mkdir(parents=True, exist_ok=True)
    
    processed = set()  # Track processed files to avoid re-dispatch
    
    while True:
        try:
            for job_file in input_dir.glob("job_*.json"):
                if job_file.name in processed:
                    continue
                
                try:
                    # Read job
                    job_data = json.loads(job_file.read_text(encoding="utf-8"))
                    job_id = job_data.get("job_id", job_file.stem.replace("job_", ""))
                    
                    print(f"[input_watcher] Found job {job_id}, dispatching to broker...")
                    
                    # Create mission/task/job in storage if not exists
                    mission_id = job_data.get("mission_id", "auto-dispatch")
                    task_id = job_data.get("task_id", "auto-dispatch-task")
                    
                    # Ensure mission exists
                    if not storage.get_mission(mission_id):
                        mission = models.Mission(
                            id=mission_id,
                            title="Auto-Dispatched Jobs",
                            description="Jobs auto-dispatched from input queue",
                            metadata={},
                            tags=["auto"],
                            created_at=datetime.now(timezone.utc).isoformat() + "Z"
                        )
                        storage.create_mission(mission)
                    
                    # Ensure task exists
                    if not storage.get_task(task_id):
                        task = models.Task(
                            id=task_id,
                            mission_id=mission_id,
                            name="Auto-Dispatch Task",
                            description="Auto-dispatch from input queue",
                            kind=job_data.get("kind", "RUN_COMMAND"),
                            params={},
                            created_at=datetime.now(timezone.utc).isoformat() + "Z"
                        )
                        storage.create_task(task)
                    
                    # Create job in storage
                    job = models.Job(
                        id=job_id,
                        task_id=task_id,
                        payload=job_data,
                        status="pending",
                        result=None,
                        created_at=datetime.now(timezone.utc).isoformat() + "Z",
                        updated_at=datetime.now(timezone.utc).isoformat() + "Z"
                    )
                    
                    # Only create if not exists
                    if not storage.get_job(job_id):
                        storage.create_job(job)
                    
                    # Dispatch to broker (offgrid)
                    correlation_id = f"auto-{uuid.uuid4().hex[:8]}"
                    
                    def run_auction():
                        try:
                            updated_job = offgrid.dispatch_job(job_id, correlation_id=correlation_id)
                            if updated_job and updated_job.status == "completed":
                                print(f"[input_watcher] Job {job_id} completed successfully")
                                # Archive the input file
                                archive_path = job_file.with_suffix(".dispatched")
                                job_file.rename(archive_path)
                            else:
                                print(f"[input_watcher] Job {job_id} dispatch failed or incomplete")
                        except Exception as e:
                            print(f"[input_watcher] ERROR dispatching {job_id}: {e}")
                    
                    import threading
                    thread = threading.Thread(target=run_auction, daemon=True)
                    thread.start()
                    
                    # Mark as processed
                    processed.add(job_file.name)
                    print(f"[input_watcher] Dispatched {job_id} to broker")
                    
                except Exception as e:
                    print(f"[input_watcher] ERROR processing {job_file.name}: {e}")
                    processed.add(job_file.name)  # Skip broken files
            
            await asyncio.sleep(5)  # Check every 5 seconds
            
        except Exception as e:
            print(f"[input_watcher] Loop error: {e}")
            await asyncio.sleep(10)


# ------------------------------------------------------------------------------
# MAIN
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    import warnings
    import os
    
    # Disable colored output
    os.environ['NO_COLOR'] = '1'
    
    # Suppress deprecation warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    
    # Run without access logs (too much spam from dashboard)
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8001,
        access_log=False  # Disable access logs completely
    )
