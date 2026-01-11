# Self-Loop API Endpoints
# Add these to main.py after the existing mission endpoints

@app.post("/api/selfloop/create")
def create_selfloop_mission(
    title: str,
    goal: str,
    initial_context: str = "",
    max_iterations: int = 10,
    constraints: list = None
):
    """
    Create a new Self-Loop mission.
    
    Args:
        title: Mission title
        goal: Main objective
        initial_context: Starting context/data
        max_iterations: Maximum loop iterations
        constraints: Optional list of constraints
    
    Returns:
        Created mission with first job dispatched
    """
    from .selfloop_prompt_builder import build_selfloop_job_payload
    
    # Create mission
    mission_create = models.MissionCreate(
        title=title,
        description=f"Self-Loop: {goal}",
        metadata={"type": "selfloop", "max_iterations": max_iterations}
    )
    mission = models.Mission.from_create(mission_create)
    storage.create_mission(mission)
    
    # Create Self-Loop task
    task_create = models.TaskCreate(
        name="selfloop_iteration",
        description="Self-Loop collaborative co-thinking",
        kind="selfloop",
        params={}
    )
    task = models.Task.from_create(mission.id, task_create)
    storage.create_task(task)
    
    # Create first job with Self-Loop payload
    job_payload = build_selfloop_job_payload(
        goal=goal,
        initial_context=initial_context or f"Mission: {title}",
        max_iterations=max_iterations,
        constraints=constraints
    )
    
    job_create = models.JobCreate(payload=job_payload)
    job = models.Job.from_create(task.id, job_create)
    storage.create_job(job)
    
    # Dispatch
    bridge.enqueue_job(job.id)
    
    return {
        "ok": True,
        "mission": mission.to_dict(),
        "task": task.to_dict(),
        "job": job.to_dict()
    }


@app.get("/api/selfloop/{mission_id}/status")
def get_selfloop_status(mission_id: str):
    """
    Get Self-Loop mission status with iteration history.
    
    Returns:
        Mission status with loop state and iteration count
    """
    mission = storage.get_mission(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    
    tasks = storage.list_tasks(mission_id)
    jobs = []
    for task in tasks:
        jobs.extend(storage.list_jobs(task.id))
    
    # Extract loop state from latest job
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


@app.post("/api/selfloop/{mission_id}/iterate")
def trigger_selfloop_iteration(mission_id: str):
    """
    Manually trigger next Self-Loop iteration.
    
    Returns:
        New job created for next iteration
    """
    mission = storage.get_mission(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail="Mission not found")
    
    tasks = storage.list_tasks(mission_id)
    if not tasks:
        raise HTTPException(status_code=400, detail="No tasks found")
    
    task = tasks[0]  # Use first task
    jobs = storage.list_jobs(task.id)
    
    if not jobs:
        raise HTTPException(status_code=400, detail="No previous jobs found")
    
    # Get latest job to extract loop state
    latest_job = jobs[-1]
    if latest_job.payload.get("job_type") != "sheratan_selfloop":
        raise HTTPException(status_code=400, detail="Not a Self-Loop mission")
    
    # The next iteration will be created automatically by _handle_selfloop_result
    # when the current job completes. This endpoint is for manual triggering.
    
    return {
        "ok": True,
        "message": "Next iteration will be created when current job completes",
        "current_job": latest_job.to_dict()
    }
