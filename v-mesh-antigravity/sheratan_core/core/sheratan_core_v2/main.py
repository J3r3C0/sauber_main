"""
Sheratan Core v2 – main.py
FastAPI Kernel for Missions → Tasks → Jobs → Worker Dispatch → LCP Followups
"""

from __future__ import annotations
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from typing import List, Optional

from . import models
from . import storage
from .webrelay_bridge import WebRelayBridge, WebRelaySettings
from .lcp_actions import LCPActionInterpreter
from .metrics_client import record_module_call, measured_call


# ------------------------------------------------------------------------------
# APP INITIALISIERUNG
# ------------------------------------------------------------------------------

app = FastAPI(
    title="Sheratan Core v2",
    description="Mission/Task/Job orchestration kernel with WebRelay & LCP",
    version="2.0.0"
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

# V1 Compatibility Layer
from .v1_compat import v1_router
app.include_router(v1_router)

# ------------------------------------------------------------------------------
# INITIALISIERUNG DER BRIDGE & LCP-ACTIONS
# ------------------------------------------------------------------------------

from .app_state import bridge, lcp


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
    return storage.list_jobs()


@app.get("/api/jobs/{job_id}", response_model=models.Job)
def get_job(job_id: str):
    j = storage.get_job(job_id)
    if j is None:
        raise HTTPException(404, "Job not found")
    return j


# ------------------------------------------------------------------------------
# JOB → WORKER DISPATCH
# ------------------------------------------------------------------------------

@app.post("/api/jobs/{job_id}/dispatch")
def dispatch_job(job_id: str):
    """
    Dispatches job to worker queue (file-based, async).
    Worker polls webrelay_out/ and makes HTTP calls to LLM.
    Also starts background polling to auto-sync results.
    """
    try:
        job_file = bridge.enqueue_job(job_id)
    except Exception as e:
        record_module_call(
            source="core_v2.api.dispatch_job",
            target="webrelay_worker",
            duration_ms=0.0,
            status="error",
            correlation_id=f"job:{job_id}",
        )
        raise HTTPException(500, f"Dispatch failed: {e}")

    # Queue-based dispatch - worker will process asynchronously
    record_module_call(
        source="core_v2.api.dispatch_job",
        target="webrelay_worker",
        duration_ms=0.0,
        status="ok",
        correlation_id=f"job:{job_id}",
    )
    
    # Start background polling for result
    import threading
    def poll_and_sync():
        import time
        max_attempts = 60  # Poll for up to 60 seconds
        for i in range(max_attempts):
            time.sleep(1)
            try:
                synced_job = bridge.try_sync_result(job_id)
                if synced_job and synced_job.result:
                    # Success! Process followups
                    print(f"[auto-sync] ✓ Got result for job {job_id[:12]}... after {i+1}s")
                    lcp.handle_job_result(synced_job)
                    break
            except Exception as e:
                # Continue polling
                pass
    
    thread = threading.Thread(target=poll_and_sync, daemon=True)
    thread.start()

    return {
        "job_id": job_id,
        "job_file": str(job_file),
        "method": "file_queue"
    }


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
# MAIN
# ------------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
