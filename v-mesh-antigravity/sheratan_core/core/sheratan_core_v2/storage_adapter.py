from .offgrid_memory import OffgridMemoryClient
from . import models
from .event_types import get_etype_for_operation
from .outbox import ReplicationOutbox
import threading
import time
from typing import List, Optional, Any

class HybridStorage:
    """
    Wraps existing storage functions with Offgrid replication and Quorum tracking.
    """
    
    def __init__(self, storage_mod: Any, offgrid_client: Optional[OffgridMemoryClient] = None):
        # Capture original functions to avoid recursion
        self._list_missions = storage_mod.list_missions
        self._get_mission = storage_mod.get_mission
        self._create_mission = storage_mod.create_mission
        self._update_mission = storage_mod.update_mission
        self._delete_mission = storage_mod.delete_mission
        
        self._list_tasks = storage_mod.list_tasks
        self._get_task = storage_mod.get_task
        self._create_task = storage_mod.create_task
        self._update_task = storage_mod.update_task
        self._find_task_by_name = storage_mod.find_task_by_name
        
        self._list_jobs = storage_mod.list_jobs
        self._get_job = storage_mod.get_job
        self._create_job = storage_mod.create_job
        self._update_job = storage_mod.update_job

        self.offgrid = offgrid_client
        self.enabled = offgrid_client is not None
        self.outbox = ReplicationOutbox() if self.enabled else None
        
        if self.enabled:
            print(f"[storage_adapter] Hybrid storage READY with Quorum tracking (Broker: {offgrid_client.broker_url})")
            # Start background worker for outbox processing
            self._worker_thread = threading.Thread(target=self._process_outbox, daemon=True)
            self._worker_thread.start()
            print(f"[storage_adapter] Outbox worker started")

    # --------------------------------------------------------------------------
    # MISSIONS
    # --------------------------------------------------------------------------

    def list_missions(self) -> List[models.Mission]:
        return self._list_missions()

    def get_mission(self, mission_id: str) -> Optional[models.Mission]:
        return self._get_mission(mission_id)

    def create_mission(self, mission: models.Mission):
        self._create_mission(mission)
        etype = get_etype_for_operation("mission", "create")
        self._replicate(f"mission:{mission.id}", mission.to_dict(), etype, required=1.0)

    def update_mission(self, mission: models.Mission):
        self._update_mission(mission)
        etype = get_etype_for_operation("mission", "update")
        self._replicate(f"mission:{mission.id}", mission.to_dict(), etype, required=1.0)

    def delete_mission(self, mission_id: str) -> bool:
        return self._delete_mission(mission_id)

    # --------------------------------------------------------------------------
    # TASKS
    # --------------------------------------------------------------------------

    def list_tasks(self) -> List[models.Task]:
        return self._list_tasks()

    def get_task(self, task_id: str) -> Optional[models.Task]:
        return self._get_task(task_id)

    def create_task(self, task: models.Task):
        self._create_task(task)
        etype = get_etype_for_operation("task", "create")
        self._replicate(f"task:{task.id}", task.to_dict(), etype, required=1.0)

    def update_task(self, task: models.Task):
        self._update_task(task)
        etype = get_etype_for_operation("task", "update")
        self._replicate(f"task:{task.id}", task.to_dict(), etype, required=1.0)

    def find_task_by_name(self, mission_id: str, name: str) -> Optional[models.Task]:
        return self._find_task_by_name(mission_id, name)

    # --------------------------------------------------------------------------
    # JOBS
    # --------------------------------------------------------------------------

    def list_jobs(self) -> List[models.Job]:
        return self._list_jobs()

    def get_job(self, job_id: str) -> Optional[models.Job]:
        return self._get_job(job_id)

    def create_job(self, job: models.Job):
        self._create_job(job)
        etype = get_etype_for_operation("job", "create")
        self._replicate(f"job:{job.id}", job.to_dict(), etype, required=1.0)

    def update_job(self, job: models.Job):
        self._update_job(job)
        etype = get_etype_for_operation("job", "update")
        self._replicate(f"job:{job.id}", job.to_dict(), etype, required=1.0)

    # --------------------------------------------------------------------------
    # REPLICATION INTERNALS
    # --------------------------------------------------------------------------

    def _replicate(self, key: str, data: dict, etype: int, required: float = 1.0):
        """Enqueue replication job to persistent outbox."""
        if not self.enabled:
            return
        self.outbox.enqueue(key, data, etype, required)
    
    def _process_outbox(self):
        """Background worker that processes pending replication jobs."""
        while True:
            try:
                jobs = self.outbox.get_pending(limit=5)
                for job in jobs:
                    try:
                        eid = self.offgrid.store_with_quorum(
                            job["key"], 
                            job["data"], 
                            job["etype"],
                            required_acks=job["required_acks"]
                        )
                        if eid:
                            self.outbox.mark_success(job["id"])
                            print(f"[outbox] ✓ Replicated {job['key']} (etype={job['etype']})")
                    except Exception as e:
                        self.outbox.mark_failed(job["id"], str(e))
                        print(f"[outbox] ✗ Failed {job['key']}: {e}")
                
                # Cleanup old completed jobs every iteration
                self.outbox.cleanup_old(max_age_hours=24)
                
                time.sleep(2)  # Poll interval
            except Exception as e:
                print(f"[outbox] Worker error: {e}")
                time.sleep(5)
