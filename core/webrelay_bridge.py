# sheratan_core_v2/webrelay_bridge.py
import json
import sys
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from core import config, storage, models

# Import mesh ledger and registry from local mesh/registry module
try:
    from mesh.registry.client import LedgerClient, PaymentRequiredError
    from mesh.registry.mesh_registry import WorkerRegistry, WorkerInfo, WorkerCapability
except ImportError:
    # Fallback if mesh.registry not in path
    LedgerClient = None
    WorkerRegistry = None
    PaymentRequiredError = None


class WebRelaySettings:
    def __init__(self, relay_out_dir: Path, relay_in_dir: Path, session_prefix: str = "core_v2"):
        self.relay_out_dir = Path(relay_out_dir)
        self.relay_in_dir = Path(relay_in_dir)
        self.session_prefix = session_prefix


class WebRelayBridge:
    """
    Handles writing unified job files for the worker and reading back results.
    """

    def __init__(self, settings: Optional[WebRelaySettings] = None):
        self.settings = settings
        
        # Standard webrelay paths (relative to BASE_DIR)
        self.relay_out_dir = config.DATA_DIR / "webrelay_out"
        self.relay_in_dir = config.DATA_DIR / "webrelay_in"
        
        self.relay_out_dir.mkdir(parents=True, exist_ok=True)
        self.relay_in_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Mesh components
        self.ledger = None
        self.registry = None
        
        if LedgerClient:
            ledger_url = os.getenv("SHERATAN_LEDGER_URL")
            # Use local ledger.json in mesh/registry/
            ledger_path = config.BASE_DIR / "mesh" / "registry" / "ledger.json"

            if ledger_url:
                self.ledger = LedgerClient(base_url=ledger_url)
            elif ledger_path.exists():
                self.ledger = LedgerClient(json_path=str(ledger_path))
                
        if WorkerRegistry:
            # Use local workers.json in mesh/registry/
            registry_path = config.BASE_DIR / "mesh" / "registry" / "workers.json"
            
            if registry_path.exists():
                self.registry = WorkerRegistry(registry_path)

    # --------------------------------------------------------------
    # KIND MAPPING FOR WORKER
    # --------------------------------------------------------------
    def _infer_job_kind(self, task: models.Task) -> str:
        """Infer job kind from task metadata."""
        # Check task.kind first (explicit)
        if task.kind and task.kind.strip():
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
        if task is None:
            raise ValueError("Task not found")

        mission = storage.get_mission(task.mission_id)
        if mission is None:
            raise ValueError("Mission not found")

        # Phase 10: Prioritize explicit kind in job payload (child jobs)
        kind = job.payload.get("kind")
        if not kind:
            kind = self._infer_job_kind(task)

        # --- MESH ARBITRAGE LOGIC ---
        worker_id = "default_worker"
        cost = 0
        
        if self.registry:
            best_worker = self.registry.get_best_worker(kind)
            if best_worker:
                worker_id = best_worker.worker_id
                # Find cost for this kind
                cost = next((c.cost for c in best_worker.capabilities if c.kind == kind), 0)
            else:
                print(f"WARNING: No specialized worker found for {kind}, using default.")

        if self.ledger and cost > 0:
            payer = mission.user_id or "default_user"
            try:
                self.ledger.charge(payer, worker_id, cost, job_id=job.id)
            except Exception as e:
                if "PaymentRequiredError" in str(type(e)):
                    raise
                print(f"Ledger charge failed: {e}")

        if self.registry:
            self.registry.record_job_start(worker_id)
            
        # Persist mesh selection in job payload for later attribution
        if "mesh" not in job.payload:
            job.payload["mesh"] = {}
        job.payload["mesh"]["worker_id"] = worker_id
        job.payload["mesh"]["cost"] = cost
        storage.update_job(job)
        # ----------------------------

        # Phase 10.3: Include artifacts from chain_context for full visibility
        artifacts = {}
        chain_id = task.params.get("chain_id")
        if chain_id:
            from core.database import get_db
            with get_db() as conn:
                ctx = storage.get_chain_context(conn, chain_id)
                if ctx:
                    artifacts = ctx.get("artifacts") or {}

        unified = {
            "job_id": job.id,
            "kind": kind,
            "worker_id": worker_id, # Target worker
            "cost": cost,           # Paid tokens
            "session_id": f"{self.settings.session_prefix if self.settings else 'core_v2'}_{mission.id}",
            "created_at": job.created_at,
            "payload": {
                "response_format": "lcp",
                "mission": mission.to_dict(),
                "task": task.to_dict(),
                "params": job.payload,
                "artifacts": artifacts, # Pass artifacts to WebRelay
                "last_result": job.payload.get("last_result") # Preserve last_result if present
            },
        }

        job_file = self.relay_out_dir / f"{job.id}.job.json"
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

        result_file = self.relay_in_dir / f"{job_id}.result.json"

        if not result_file.exists():
            return None

        try:
            raw = result_file.read_text()
            print(f"[bridge] 📨 Syncing result for job {job_id[:8]}... RAW length: {len(raw)}")
            content = json.loads(raw)
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
        
        # --- MESH SETTLEMENT & STATS ---
        if self.registry:
            mesh_data = job.payload.get("mesh", {})
            worker_id = mesh_data.get("worker_id")
            if worker_id:
                # 1. Arbitrage Settlement
                if job.status == "completed" and self.ledger:
                    try:
                        # Extract payout details
                        payer_id = job.payload.get("payer_id", "default_user")
                        total_cost = float(mesh_data.get("cost", 0))
                        
                        if total_cost > 0:
                            # Governance: Dynamic Margin
                            margin = None
                            worker = self.registry.workers.get(worker_id)
                            if worker:
                                stats = worker.stats
                                # Use calculate_margin helper from ledger
                                if hasattr(self.ledger, '_service') and self.ledger._service:
                                    margin = self.ledger._service.calculate_margin(
                                        stats.success_ema, stats.latency_ms_ema
                                    )
                            
                            success = self.ledger.charge_and_settle(
                                payer_id=payer_id,
                                worker_id=worker_id,
                                total_amount=total_cost,
                                job_id=job_id,
                                margin=margin,
                                note=f"Bridge settlement for job {job_id[:8]}"
                            )
                            if success:
                                margin_pct = f" (margin: {margin*100:.1f}%)" if margin else ""
                                print(f"[bridge] 💰 Settled job {job_id[:8]}: {total_cost} TOK{margin_pct}")
                            else:
                                print(f"[bridge] ⚠️ Settlement failed for job {job_id[:8]} (likely insufficient balance)")
                    except Exception as e:
                        print(f"[bridge] ❌ Error during settlement: {e}")

                # 2. Record Performance Stats
                try:
                    created_dt = datetime.fromisoformat(job.created_at.replace("Z", "+00:00"))
                    now_dt = datetime.now(created_dt.tzinfo)
                    latency_ms = (now_dt - created_dt).total_seconds() * 1000
                    
                    is_ok = job.status == "completed"
                    self.registry.record_worker_result(worker_id, latency_ms, is_ok)
                    print(f"[bridge] 📊 Recorded results for {worker_id}: {latency_ms:.0f}ms, success={is_ok}")
                except Exception as e:
                    print(f"[bridge] Warning: Could not record mesh stats: {e}")
        # -------------------------------

        storage.update_job(job)

        if remove_after_read:
            result_file.unlink(missing_ok=True)

        # NOTE: LCP interpreter call removed from here. 
        # It is now handled centrally in main.py:sync_job to avoid double execution.
        
        return job
