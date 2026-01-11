from fastapi import APIRouter, HTTPException, Request
from . import models
from . import storage
from .app_state import bridge, lcp
from typing import List, Dict, Any

v1_router = APIRouter(prefix="/v1")

@v1_router.post("/missions")
async def v1_create_mission(payload: Dict[str, Any]):
    # V1 compatibility: translate fields if necessary
    m_create = models.MissionCreate(
        title=payload.get("title", "Legacy Mission"),
        description=payload.get("description", ""),
        metadata=payload.get("metadata", {})
    )
    mission = models.Mission.from_create(m_create)
    storage.create_mission(mission)
    return {"id": mission.id, "state": "created"}

@v1_router.post("/jobs")
async def v1_create_job(payload: Dict[str, Any]):
    # V1 requires a mission/task context. We'll create a default one if missing.
    mission_id = payload.get("mission_id")
    if not mission_id:
        # Create a transient mission for this job
        m = models.Mission.from_create(models.MissionCreate(title="V1 Job Container", description=""))
        storage.create_mission(m)
        mission_id = m.id
    
    task_id = payload.get("task_id")
    if not task_id:
        t = models.Task.from_create(mission_id, models.TaskCreate(name="v1_task", description="", kind="v1_compat"))
        storage.create_task(t)
        task_id = t.id

    job = models.Job.from_create(task_id, models.JobCreate(payload=payload.get("envelope", payload)))
    storage.create_job(job)
    return {"id": job.id, "state": job.status}

@v1_router.get("/jobs/next")
async def v1_get_next_job(consumer: str = "worker", instance_id: str = "default"):
    # Find a pending job
    jobs = storage.list_jobs()
    pending = [j for j in jobs if j.status == "pending"]
    if not pending:
        return None
    
    job = pending[0]
    # Lease it
    job.status = "leased"
    if not hasattr(job, "metadata") or job.metadata is None:
        job.metadata = {}
    job.metadata["leased_by"] = consumer
    job.metadata["instance_id"] = instance_id
    storage.update_job(job)
    
    return {
        "id": job.id,
        "envelope": job.payload,
        "state": "leased",
        "lease": {"leased_by": consumer, "instance_id": instance_id}
    }

@v1_router.post("/results")
async def v1_post_result(payload: Dict[str, Any]):
    job_id = payload.get("job_id")
    if not job_id:
        raise HTTPException(400, "Missing job_id")
    
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    # Simulate sync_job logic
    job.result = payload.get("result", {})
    job.status = "completed"
    storage.update_job(job)
    
    # Process LCP followups
    lcp.handle_job_result(job)
    
    return {"ok": True, "job_id": job_id, "state": "completed"}

@v1_router.get("/jobs/{job_id}")
async def v1_get_job_state(job_id: str):
    job = storage.get_job(job_id)
    if not job:
        raise HTTPException(404, "Job not found")
    
    return {
        "id": job.id,
        "state": "completed" if job.status == "completed" else "active",
        "result": job.result
    }

@v1_router.post("/maintenance/leases/reap")
async def v1_reap_leases():
    return {"reaped_count": 0}
