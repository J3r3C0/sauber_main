# sheratan_core_v2/webrelay_http_client.py
"""
HTTP client for WebRelay API.
Replaces file-based communication with direct HTTP calls.
"""

import requests
from typing import Optional, Dict, Any
from datetime import datetime

from . import storage, models


class WebRelayHTTPClient:
    """HTTP client for WebRelay API."""
    
    def __init__(self, base_url: str = "http://localhost:3000"):
        self.base_url = base_url.rstrip('/')
    
    def submit_job(self, job: models.Job, task: models.Task, mission: models.Mission) -> Optional[Dict[str, Any]]:
        """
        Submit a job to WebRelay via HTTP API.
        
        Args:
            job: Job object
            task: Task object  
            mission: Mission object
            
        Returns:
            Response from WebRelay or None on error
        """
        # Build unified job payload
        unified_job = {
            "job_id": job.id,
            "kind": task.kind or "llm_call",
            "session_id": f"core_v2_{mission.id}",
            "created_at": job.created_at,
            "payload": {
                "response_format": "lcp",
                "mission": mission.to_dict(),
                "task": task.to_dict(),
                "params": job.payload,
            },
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/api/job/submit",
                json=unified_job,
                timeout=120  # 2 minutes for LLM response
            )
            response.raise_for_status()
            result = response.json()
            
            # Update job with result
            job.result = result
            if result.get("ok", False):
                job.status = "completed"
            else:
                job.status = "failed"
            job.updated_at = datetime.utcnow().isoformat() + "Z"
            storage.update_job(job)
            
            return result
            
        except requests.exceptions.Timeout:
            job.status = "failed"
            job.result = {"ok": False, "error": "WebRelay timeout"}
            job.updated_at = datetime.utcnow().isoformat() + "Z"
            storage.update_job(job)
            return None
            
        except Exception as e:
            job.status = "failed"
            job.result = {"ok": False, "error": str(e)}
            job.updated_at = datetime.utcnow().isoformat() + "Z"
            storage.update_job(job)
            return None
    
    def health_check(self) -> bool:
        """Check if WebRelay is available."""
        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)
            return response.status_code == 200
        except:
            return False
