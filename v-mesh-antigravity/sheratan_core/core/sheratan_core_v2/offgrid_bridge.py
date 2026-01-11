"""
Offgrid Bridge - HTTP Client for Offgrid Broker communication.

Handles dispatching Core jobs to the Offgrid Broker for auction,
and retrieving results from the winning host.
"""

import json
import time
import hmac
import hashlib
import uuid
import base64
import requests
from typing import Optional, Dict, Any
from dataclasses import dataclass

from . import models, storage
from .schema_mapping import core_to_offgrid_job, offgrid_to_core_result


@dataclass
class OffgridConfig:
    """Configuration for Offgrid integration."""
    broker_url: str = "http://127.0.0.1:9000"
    auth_key: str = "shared-secret"
    mode: str = "auto"  # auto | offgrid | disabled
    timeout_s: float = 30.0
    max_retries: int = 3
    retry_delay_s: float = 2.0


class OffgridBridgeError(Exception):
    """Base exception for Offgrid Bridge errors."""
    pass


class BrokerUnavailable(OffgridBridgeError):
    """Broker is not reachable."""
    pass


class NoHostsAvailable(OffgridBridgeError):
    """No hosts available for job execution."""
    pass


class JobTimeout(OffgridBridgeError):
    """Job execution timeout."""
    pass


class OffgridBridge:
    """
    HTTP Bridge to Offgrid Broker.
    
    Provides methods to:
    - Dispatch jobs to Broker for auction
    - Poll for job results
    - Handle errors and retries
    """
    
    def __init__(self, config: OffgridConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "SheratanCore/2.0"
        })
    
    def is_available(self) -> bool:
        """
        Check if Offgrid Broker is available.
        
        Returns:
            True if broker responds to health check
        """
        try:
            response = self.session.get(
                f"{self.config.broker_url}/status",
                timeout=2.0
            )
            return response.status_code == 200
        except Exception:
            return False
    
    def dispatch_job(self, job_id: str, correlation_id: Optional[str] = None) -> Optional[models.Job]:
        """
        Dispatch a job to Offgrid Broker for auction and execution.
        
        Flow:
        1. Load job, task, mission from storage
        2. Convert to Offgrid schema
        3. POST to Broker /auction
        4. Poll for result
        5. Convert result back to Core schema
        6. Update job in storage
        
        Args:
            job_id: Core job ID
        
        Returns:
            Updated job object or None if failed
        
        Raises:
            BrokerUnavailable: If broker is not reachable
            NoHostsAvailable: If no hosts accept the job
            JobTimeout: If job execution times out
        """
        
        # Load job from storage
        job = storage.get_job(job_id)
        if job is None:
            raise ValueError(f"Job {job_id} not found")
        
        task = storage.get_task(job.task_id)
        if task is None:
            raise ValueError(f"Task {job.task_id} not found")
        
        mission = storage.get_mission(task.mission_id)
        if mission is None:
            raise ValueError(f"Mission {task.mission_id} not found")
        
        # Convert to Offgrid schema (Legacy support for auction metadata)
        offgrid_legacy = core_to_offgrid_job(job, task, mission)
        
        # --- NEW JOBSPEC v1 CONTRACT ---
        attempt_id = str(uuid.uuid4())
        kind = task.kind or "unknown"
        
        # Map args based on kind
        args = {}
        if kind == "write_file":
            # Map Sheratan Core params to Host Contract
            # Task params: {'file': '...', 'content': '...'} or Job payload
            path = job.payload.get("file") or task.params.get("file")
            content = job.payload.get("content") or task.params.get("content") or ""
            
            if isinstance(content, str):
                content_b64 = base64.b64encode(content.encode("utf-8")).decode("utf-8")
            else:
                content_b64 = ""
            
            args = {
                "path": path,
                "content_b64": content_b64,
                "limit_mb": 10
            }
        else:
            # Fallback for other kinds
            args = {**task.params, **job.payload}

        deadline_ts = int(time.time()) + 300 # 5 min deadline

        job_spec_v1 = {
            "contract_version": 1,
            "job_id": job_id,
            "req_uid": correlation_id, # Correlation ID / request_id
            "attempt_id": attempt_id,
            "kind": kind,
            "args": args,
            "deadline_ts": deadline_ts
        }

        # Sign for AUTHZ (Claim Token)
        claim_token = self._generate_claim_token(job_spec_v1)
        job_spec_v1["claim_token"] = claim_token

        # Combine for Auction (Broker needs the legacy fields for its auction logic)
        full_payload = {
            **offgrid_legacy,
            "job": job_spec_v1, # Host will look for this
            "timestamp": int(time.time()),
            "req_id": correlation_id # Pass through for Broker logs
        }
        
        # Sign the whole payload for the Broker
        signed_payload = self._sign_payload(full_payload)
        
        print(f"[offgrid_bridge] Dispatching job {job_id[:8]} (req={correlation_id}) to {self.config.broker_url}")
        
        # POST to Broker with retries
        for attempt in range(self.config.max_retries):
            try:
                response = self.session.post(
                    f"{self.config.broker_url}/auction",
                    json=signed_payload,
                    timeout=self.config.timeout_s
                )
                
                if response.status_code == 200:
                    result = response.json()
                    host_id = result.get('host', 'unknown-host')
                    print(f"[offgrid_bridge] Auction successful: host={host_id}, req={correlation_id}")
                    
                    # Convert result to Core schema
                    core_result = offgrid_to_core_result(result)
                    
                    # Log CLAIMED event
                    storage.create_job_event(models.JobEvent.create(
                        job_id, "CLAIMED", host_id=host_id, 
                        metadata={"quote": result.get('quote'), "req_id": correlation_id}
                    ))
                    
                    # Update job
                    job.result = core_result
                    job.status = models.JobStatus.COMPLETED if core_result.get("ok") else models.JobStatus.FAILED
                    from datetime import datetime
                    job.updated_at = datetime.utcnow().isoformat() + "Z"
                    storage.update_job(job)
                    
                    # Log FINISHED/FAILED event
                    event_type = "FINISHED" if core_result.get("ok") else "FAILED"
                    storage.create_job_event(models.JobEvent.create(
                        job_id, event_type, host_id=host_id, metadata={"result_summary": core_result.get("summary", "No summary")}
                    ))
                    
                    return job
                
                elif response.status_code == 503:
                    # No hosts available
                    print(f"[offgrid_bridge] No hosts available (attempt {attempt + 1}/{self.config.max_retries})")
                    if attempt < self.config.max_retries - 1:
                        time.sleep(self.config.retry_delay_s * (2 ** attempt))
                    continue
                
                else:
                    print(f"[offgrid_bridge] Broker error: {response.status_code} {response.text}")
                    raise BrokerUnavailable(f"Broker returned {response.status_code}")
            
            except requests.exceptions.Timeout:
                print(f"[offgrid_bridge] Timeout (attempt {attempt + 1}/{self.config.max_retries})")
                if attempt < self.config.max_retries - 1:
                    time.sleep(self.config.retry_delay_s * (2 ** attempt))
                continue
            
            except requests.exceptions.ConnectionError as e:
                print(f"[offgrid_bridge] Connection error: {e}")
                raise BrokerUnavailable(f"Cannot connect to broker: {e}")
        
        # All retries exhausted
        raise NoHostsAvailable(f"No hosts available after {self.config.max_retries} attempts")
    
    def _generate_claim_token(self, spec: Dict[str, Any]) -> str:
        """Generate an HMAC claim token for the host to verify."""
        msg = f"{spec['job_id']}:{spec['attempt_id']}:{spec['deadline_ts']}"
        return hmac.new(
            self.config.auth_key.encode(),
            msg.encode(),
            hashlib.sha256
        ).hexdigest()

    def _sign_payload(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sign payload with HMAC-SHA256 for Broker authentication.
        """
        # Recreate signature
        payload_str = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            self.config.auth_key.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return {
            **payload,
            "signature": signature
        }
    
    def verify_signature(self, payload: Dict[str, Any]) -> bool:
        """
        Verify HMAC signature of payload.
        
        Args:
            payload: Payload with signature field
        
        Returns:
            True if signature is valid
        """
        
        if "signature" not in payload:
            return False
        
        received_sig = payload.pop("signature")
        
        # Recreate signature
        payload_str = json.dumps(payload, sort_keys=True)
        expected_sig = hmac.new(
            self.config.auth_key.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(received_sig, expected_sig)
