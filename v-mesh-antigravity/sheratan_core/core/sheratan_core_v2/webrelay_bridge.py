# sheratan_core_v2/webrelay_bridge.py
import json
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from . import storage, models


class WebRelaySettings:
    def __init__(self, relay_out_dir: Path, relay_in_dir: Path, session_prefix: str = "core_v2"):
        self.relay_out_dir = Path(relay_out_dir)
        self.relay_in_dir = Path(relay_in_dir)
        self.session_prefix = session_prefix


class WebRelayBridge:
    """
    Handles writing unified job files for the worker and reading back results.
    """

    def __init__(self, settings: WebRelaySettings):
        self.settings = settings

        # Dynamic dirs do not depend on settings for correctness
        (Path("C:/projectroot/v_mesh_output")).mkdir(parents=True, exist_ok=True)
        (Path("C:/projectroot/v_mesh_inbox")).mkdir(parents=True, exist_ok=True)

    # --------------------------------------------------------------
    # KIND MAPPING FOR WORKER
    # --------------------------------------------------------------
    def _infer_job_kind(self, task: models.Task) -> str:
        """Infer job kind from task metadata."""
        # Check task.kind first (explicit)
        if task.kind:
            return task.kind
        
        # Fallback: infer from task name
        name = task.name.lower()

        # Discovery → list_files
        if "discovery" in name or "list_files" in name:
            return "list_files"

        # Analyzer
        if "analyze" in name:
            return "analyze_file"

        # Writer
        if "write" in name:
            return "write_file"

        # Patcher
        if "update" in name or "patch" in name:
            return "patch_file"

        return "llm_call"


    # --------------------------------------------------------------
    # WRITE UNIFIED JOB FILE
    # --------------------------------------------------------------
    def enqueue_job(self, job_id: str) -> Path:
        job = storage.get_job(job_id)
        if job is None:
            raise ValueError("Job not found")

        task = storage.get_task(job.task_id)
        print("DEBUG task.name =", repr(task.name))
        if task is None:
            raise ValueError("Task not found")

        mission = storage.get_mission(task.mission_id)
        if mission is None:
            raise ValueError("Mission not found")

        kind = self._infer_job_kind(task)

        unified = {
            "job_id": job.id,
            "kind": kind,
            "session_id": f"{self.settings.session_prefix}_{mission.id}",
            "created_at": job.created_at,
            "payload": {
                "response_format": "lcp",
                "mission": mission.to_dict(),
                "task": task.to_dict(),
                "params": job.payload,
            },
        }

        out_dir = Path("C:/projectroot/v_mesh_output")
        out_dir.mkdir(parents=True, exist_ok=True)

        job_file = out_dir / f"{job.id}.job.json"
        with open(job_file, "w", encoding="utf-8") as f:
            json.dump(unified, f, indent=2)

        return job_file

    # --------------------------------------------------------------
    # READ AND PROCESS RESULT FILES
    # --------------------------------------------------------------
    def try_sync_result(self, job_id: str, remove_after_read: bool = True) -> Optional[models.Job]:
        job = storage.get_job(job_id)
        if job is None:
            return None

        in_dir = Path("C:/projectroot/v_mesh_inbox")
        result_file = in_dir / f"{job_id}.result.json"

        if not result_file.exists():
            return None

        try:
            content = json.loads(result_file.read_text())
        except Exception:
            job.status = "failed"
            job.result = {"ok": False, "error": "invalid_json"}
            job.updated_at = datetime.utcnow().isoformat() + "Z"
            storage.update_job(job)
            if remove_after_read:
                result_file.unlink(missing_ok=True)
            return job

        job.result = content
        if not content.get("ok", True):
            job.status = "failed"
        else:
            job.status = "completed"

        job.updated_at = datetime.utcnow().isoformat() + "Z"
        storage.update_job(job)

        if remove_after_read:
            result_file.unlink(missing_ok=True)

        return job
