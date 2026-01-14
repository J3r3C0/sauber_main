import time
import uuid
import logging
import threading
from typing import Optional, Dict, Any, List

from core import storage
from core.database import get_db
from core.job_chain_manager import JobChainManager
from core.models import Job

class ChainRunner:
    """
    Heartbeat Runner for Autonomous Chains.
    Polls active chains and dispatches pending specifications as jobs.
    """

    def __init__(
        self,
        storage_mod=storage,
        poll_interval_sec: float = 1.0,
        lease_seconds: int = 120,
        logger=None,
        agent_plan_kind: str = "agent_plan"
    ):
        self.storage = storage_mod
        self.poll_interval_sec = poll_interval_sec
        self.lease_seconds = lease_seconds
        self.logger = logger or logging.getLogger("chain_runner")
        
        # Initialize manager (needed for resolution)
        from core.chain_index import ChainIndex
        chain_dir = self.storage.DATA_DIR / "chains"
        chain_index_path = self.storage.DATA_DIR / "chain_index.db"
        
        self.chain_manager = JobChainManager(
            chain_dir=str(chain_dir),
            chain_index=ChainIndex(str(chain_index_path)),
            storage=storage_mod,
            logger=self.logger,
            agent_plan_kind=agent_plan_kind
        )
        
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        """Start the runner in a background thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="ChainRunner")
        self._thread.start()
        self.logger.info("ChainRunner started.")

    def stop(self):
        """Stop the runner."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        self.logger.info("ChainRunner stopped.")

    def _run_loop(self):
        print(f"[chain_runner] Heartbeat loop started.")
        while not self._stop_event.is_set():
            try:
                processed_count = self.tick()
                if processed_count == 0:
                    # Idle backoff
                    time.sleep(self.poll_interval_sec)
                else:
                    print(f"[chain_runner] Processed {processed_count} specs in this tick.")
            except Exception as e:
                print(f"[chain_runner] Error in loop: {e}")
                self.logger.error(f"Error in ChainRunner loop: {e}", exc_info=True)
                time.sleep(5) # Error backoff

    def tick(self) -> int:
        processed = 0
        with get_db() as conn:
            # 1. Find chains that need attention
            chain_ids = self.storage.list_chains_needing_tick(conn, limit=20)
            if not chain_ids:
                return 0
            
            for cid in chain_ids:
                if self._stop_event.is_set():
                    break
                
                # 2. Update tick time for fairness (round-robin)
                self.storage.update_chain_tick_time(conn, cid)
                
                # 3. Try to claim one spec
                spec = self.storage.claim_next_pending_spec(conn, cid, lease_seconds=self.lease_seconds)
                if not spec:
                    self.logger.info(f"[chain:{cid}] No spec claimed.")
                    # No pending specs? Double check if we should clear needs_tick
                    all_pending = self.storage.list_pending_chain_specs(conn, cid, limit=1)
                    if not all_pending:
                        self.logger.info(f"[chain:{cid}] No more pending specs, clearing needs_tick.")
                        self.storage.set_chain_needs_tick(conn, cid, False)
                    continue

                # 4. Process the spec
                self.logger.info(f"[chain:{cid}] Claimed spec {spec['spec_id']}")
                try:
                    self._process_spec(cid, spec)
                    processed += 1
                except Exception as e:
                    self.logger.error(f"[chain:{cid}] Error processing spec {spec['spec_id']}: {e}")
                    # Leave it geclaimed; lease will eventually expire for retry
                    
        return processed

    def _process_spec(self, chain_id: str, spec: Dict[str, Any]):
        """Resolve and dispatch a single spec."""
        spec_id = spec["spec_id"]
        claim_id = spec["claim_id"]
        
        # 1. Resolve parameters (result-refs, etc)
        # resolve_chain_spec handles persistence of resolved_params_json internally
        resolved_params = self.chain_manager.resolve_chain_spec(chain_id=chain_id, spec_id=spec_id)
        
        # 2. Create the real Job entity
        job_id = str(uuid.uuid4())
        ts = self.storage._now_iso()
        
        # Build payload with chain metadata
        payload = {
            "kind": spec["kind"],
            "params": resolved_params,
            "_chain_hint": {
                "chain_id": chain_id,
                "root_job_id": spec["root_job_id"],
                "parent_job_id": spec["parent_job_id"],
                "spec_id": spec_id,
                "role": "child"
            }
        }
        
        
        # Determine dependencies: root jobs have no deps, child jobs depend on real parent
        parent_id = (spec.get("parent_job_id") or "").strip()
        depends_on = [parent_id] if parent_id and parent_id not in {"parent", "root", ""} else []
        
        job = Job(
            id=job_id,
            task_id=spec["task_id"],
            payload=payload,
            status="pending",
            result=None,
            retry_count=0,
            idempotency_key=f"spec:{spec_id}",
            priority="normal",
            timeout_seconds=300,
            depends_on=depends_on,
            created_at=ts,
            updated_at=ts,
        )
        
        # 3. Persist job and mark spec as dispatched (ideally atomic, but idempotency helps)
        with get_db() as conn:
            # Persist Job
            self.storage.create_job_with_conn(conn, job)
            
            # Mark Spec as Dispatched
            self.storage.mark_chain_spec_dispatched(
                conn, 
                chain_id=chain_id, 
                spec_id=spec_id, 
                job_id=job_id, 
                claim_id=claim_id
            )
            
            # Ensure chain still ticks if there are more specs
            self.storage.set_chain_needs_tick(conn, chain_id, True)
            
        self.logger.info(f"[chain:{chain_id}] Dispatched job {job_id} for spec {spec_id}")
