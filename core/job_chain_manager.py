# core/job_chain_manager.py
"""
Job Chain Manager - Event-driven State Machine for LCP Job Chaining
Zero-intrusion approach using chain_index for metadata
"""

import os
import json
import time
import uuid
import hashlib
import tempfile
from typing import Any, Dict, List, Optional

from core.chain_index import ChainIndex


def now_iso() -> str:
    """ISO timestamp for logs/state."""
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def atomic_write_json(path: str, data: Dict[str, Any]) -> None:
    """Atomic write using temp file + replace."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    d = os.path.dirname(path)
    fd, tmp = tempfile.mkstemp(prefix="tmp_", suffix=".json", dir=d)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        os.replace(tmp, path)
    finally:
        try:
            if os.path.exists(tmp):
                os.remove(tmp)
        except Exception:
            pass


def load_json(path: str, default: Dict[str, Any]) -> Dict[str, Any]:
    """Load JSON file with default fallback."""
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def canonical_hash(kind: str, params: Dict[str, Any]) -> str:
    """Deterministic hash of (kind, params) for repeat detection."""
    payload = {"kind": kind, "params": params}
    blob = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


class JobChainManager:
    """
    Event-driven chaining:
    - agent_plan returns LCP followup jobs
    - Core calls register_followup_jobs()
    - Dispatcher executes child jobs, completes them
    - Core calls on_job_complete() for every completion
    - When pending empty -> dispatch_next_llm_step() creates new agent_plan job (pending)
    """

    def __init__(
        self,
        *,
        chain_dir: str,
        chain_index: ChainIndex,
        storage,  # storage module (create_job/get_job/update_job)
        logger=None,
        agent_plan_kind: str = "agent_plan",
        default_max_depth: int = 5,
        default_max_jobs_total: int = 25,
        default_timeout_seconds: int = 300,
        max_result_chars_per_child: int = 25_000,
    ):
        self.chain_dir = chain_dir
        self.chain_index = chain_index
        self.storage = storage
        self.logger = logger
        self.agent_plan_kind = agent_plan_kind

        self.default_max_depth = default_max_depth
        self.default_max_jobs_total = default_max_jobs_total
        self.default_timeout_seconds = default_timeout_seconds
        self.max_result_chars_per_child = max_result_chars_per_child

        os.makedirs(self.chain_dir, exist_ok=True)

    # -------------------------
    # Chain State Persistence
    # -------------------------

    def _chain_path(self, chain_id: str) -> str:
        return os.path.join(self.chain_dir, f"{chain_id}.json")

    def ensure_chain(self, *, chain_id: str, root_job_id: str) -> Dict[str, Any]:
        """Create chain file if missing; return chain dict."""
        path = self._chain_path(chain_id)
        chain = load_json(path, default={})
        if chain:
            return chain

        now = int(time.time())
        chain = {
            "chain_id": chain_id,
            "root_job_id": root_job_id,
            "last_llm_job_id": root_job_id,
            "depth": 0,
            "max_depth": self.default_max_depth,
            "max_jobs_total": self.default_max_jobs_total,
            "jobs_total": 0,
            "timeout_at": now + self.default_timeout_seconds,
            "status": "WAITING_LLM",
            "requested_hashes": [],
            "pending_child_job_ids": [],
            "child_results": {},
            "last_tool_results": [],
            "final_answer": None,
            "failed_reason": None,
            "updated_at": now_iso(),
        }
        atomic_write_json(path, chain)

        # chain_index for root job
        self.chain_index.put(root_job_id, {
            "chain_id": chain_id,
            "role": "llm_step",
            "root_job_id": root_job_id,
            "parent_llm_job_id": None,
            "depth": 0
        })
        return chain

    def load_chain(self, chain_id: str) -> Dict[str, Any]:
        """Load chain json."""
        return load_json(self._chain_path(chain_id), default={})

    def save_chain(self, chain: Dict[str, Any]) -> None:
        """Save chain json with timestamp."""
        chain["updated_at"] = now_iso()
        atomic_write_json(self._chain_path(chain["chain_id"]), chain)

    # -------------------------
    # Guards
    # -------------------------

    def _guard_allow_jobs(self, chain: Dict[str, Any], job_specs: List[Dict[str, Any]]) -> Optional[str]:
        """
        Return None if allowed, else string reason.
        Enforces: depth, jobs_total, timeout, repeat detector.
        """
        now = int(time.time())

        if chain.get("status") in ("DONE", "FAILED"):
            return f"chain_not_active:{chain.get('status')}"

        if now > int(chain["timeout_at"]):
            return "timeout_exceeded"

        if int(chain["depth"]) >= int(chain["max_depth"]):
            return "max_depth_reached"

        if int(chain["jobs_total"]) + len(job_specs) > int(chain["max_jobs_total"]):
            return "max_jobs_total_exceeded"

        # repeat detector
        requested = set(chain.get("requested_hashes", []))
        for spec in job_specs:
            kind = str(spec.get("kind", "")).strip()
            params = spec.get("params") or {}
            if not kind or not isinstance(params, dict):
                return "invalid_job_spec"
            h = canonical_hash(kind, params)
            if h in requested:
                return "repeat_detected"
        return None

    def _compact_child_result(self, job_kind: str, result: Dict[str, Any]) -> Dict[str, Any]:
        """Compact + truncate huge content deterministically."""
        blob = json.dumps(result, ensure_ascii=False)
        if len(blob) <= self.max_result_chars_per_child:
            return {"kind": job_kind, "result": result, "truncated": False}

        # truncate by string length; keep prefix
        truncated_blob = blob[: self.max_result_chars_per_child]
        return {
            "kind": job_kind,
            "result": {
                "_truncated_json_prefix": truncated_blob,
                "_note": "Result too large; stored as truncated JSON prefix."
            },
            "truncated": True,
        }

    # -------------------------
    # REQUIRED: register_followup_jobs()
    # -------------------------

    def register_followup_jobs(
        self,
        *,
        chain_id: str,
        root_job_id: str,
        parent_llm_job_id: str,
        job_specs: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Creates child jobs via storage.create_job(job).
        Adds routing info to chain_index for each child job.
        Updates chain state: pending list, depth/jobs_total, requested_hashes, status.
        """
        chain = self.ensure_chain(chain_id=chain_id, root_job_id=root_job_id)

        # Guard checks
        reason = self._guard_allow_jobs(chain, job_specs)
        if reason is not None:
            chain["failed_reason"] = reason
            self.save_chain(chain)
            if self.logger:
                self.logger.warning(f"[chain:{chain_id}] followups rejected: {reason}")
            # trigger another llm step with constraint info
            self.dispatch_next_llm_step(chain_id=chain_id, constraint_violation=reason)
            return {"ok": False, "reason": reason, "dispatched": 0, "child_job_ids": []}

        child_job_ids: List[str] = []

        next_depth = int(chain["depth"]) + 1
        chain["depth"] = next_depth
        chain["status"] = "WAITING_CHILDREN"
        chain["failed_reason"] = None

        # Record repeat hashes and create child jobs
        for spec in job_specs:
            kind = str(spec["kind"]).strip()
            params = spec.get("params") or {}
            h = canonical_hash(kind, params)
            chain.setdefault("requested_hashes", []).append(h)

            # Create Job object
            job_id = str(uuid.uuid4())
            created = now_iso()

            payload = {
                "kind": kind,
                "params": params,
                "_chain_hint": {
                    "chain_id": chain_id,
                    "root_job_id": root_job_id,
                    "parent_llm_job_id": parent_llm_job_id,
                    "depth": next_depth,
                    "role": "child"
                }
            }

            depends_on = [parent_llm_job_id]

            from core.models import Job

            job = Job(
                id=job_id,
                task_id=root_job_id,
                payload=payload,
                status="pending",
                result=None,
                retry_count=0,
                idempotency_key=f"chain:{chain_id}:{h}",
                priority="normal",
                timeout_seconds=300,
                depends_on=depends_on,
                created_at=created,
                updated_at=created,
            )

            # Persist job (dispatcher loop will pick it up)
            self.storage.create_job(job)

            # Chain index routing
            self.chain_index.put(job_id, {
                "chain_id": chain_id,
                "role": "child",
                "root_job_id": root_job_id,
                "parent_llm_job_id": parent_llm_job_id,
                "depth": next_depth,
            })

            child_job_ids.append(job_id)

        chain["jobs_total"] = int(chain["jobs_total"]) + len(child_job_ids)
        chain["pending_child_job_ids"] = list(set(chain.get("pending_child_job_ids", [])) | set(child_job_ids))
        chain["last_llm_job_id"] = parent_llm_job_id
        self.save_chain(chain)

        if self.logger:
            self.logger.info(f"[chain:{chain_id}] dispatched {len(child_job_ids)} child jobs at depth={next_depth}")

        return {"ok": True, "reason": None, "dispatched": len(child_job_ids), "child_job_ids": child_job_ids}

    # -------------------------
    # REQUIRED: on_job_complete()
    # -------------------------

    def on_job_complete(self, *, job_id: str, result: Dict[str, Any]) -> None:
        """
        Called by core when ANY job completes.
        If job_id is a child job in a chain:
          - store compact result
          - remove from pending
          - if pending empty: dispatch_next_llm_step()
        """
        info = self.chain_index.get(job_id)
        if not info:
            return

        if info.get("role") != "child":
            return

        chain_id = info["chain_id"]
        chain = self.load_chain(chain_id)
        if not chain:
            return

        if chain.get("status") in ("DONE", "FAILED"):
            return

        # Determine child kind from job payload
        try:
            job = self.storage.get_job(job_id)
            job_kind = (job.payload or {}).get("kind") or "unknown"
        except Exception:
            job_kind = "unknown"

        compact = self._compact_child_result(job_kind, result)

        # Save result
        chain.setdefault("child_results", {})[job_id] = compact
        chain.setdefault("last_tool_results", []).append({
            "job_id": job_id,
            **compact
        })

        # Remove pending
        pending = set(chain.get("pending_child_job_ids", []))
        if job_id in pending:
            pending.remove(job_id)
        chain["pending_child_job_ids"] = list(pending)

        # Check timeout
        now = int(time.time())
        if now > int(chain["timeout_at"]):
            chain["status"] = "FAILED"
            chain["failed_reason"] = "timeout_exceeded"
            self.save_chain(chain)
            if self.logger:
                self.logger.warning(f"[chain:{chain_id}] FAILED: timeout_exceeded")
            return

        # If no more pending -> ask LLM for next step
        if len(chain["pending_child_job_ids"]) == 0:
            self.save_chain(chain)
            self.dispatch_next_llm_step(chain_id=chain_id)
        else:
            self.save_chain(chain)

    # -------------------------
    # REQUIRED: dispatch_next_llm_step()
    # -------------------------

    def dispatch_next_llm_step(self, *, chain_id: str, constraint_violation: Optional[str] = None) -> Optional[str]:
        """
        Creates a new agent_plan job (pending) via storage.create_job().
        Payload includes aggregated tool results and chain context.
        Returns new llm job id (or None on failure).
        """
        chain = self.load_chain(chain_id)
        if not chain:
            return None

        if chain.get("status") in ("DONE", "FAILED"):
            return None

        # Guard: depth max
        if int(chain["depth"]) >= int(chain["max_depth"]) and constraint_violation is None:
            constraint_violation = "max_depth_reached"

        # Load root job to recover original user request
        try:
            root_job = self.storage.get_job(chain["root_job_id"])
        except Exception:
            root_job = None

        # Extract original user request
        user_request = None
        if root_job is not None:
            p = root_job.payload or {}
            user_request = p.get("user_request")
            if user_request is None and isinstance(p.get("params"), dict):
                user_request = p["params"].get("user_request")
            if user_request is None:
                user_request = p.get("prompt") or p.get("input") or p.get("text")

        # Aggregated tool results
        tool_results = chain.get("last_tool_results", [])

        llm_input = {
            "lcp_version": "1",
            "purpose": "job_chaining_orchestrator",
            "chain": {
                "chain_id": chain_id,
                "root_job_id": chain["root_job_id"],
                "last_llm_job_id": chain.get("last_llm_job_id"),
                "depth": int(chain["depth"]),
                "max_depth": int(chain["max_depth"]),
                "jobs_total": int(chain["jobs_total"]),
                "max_jobs_total": int(chain["max_jobs_total"]),
                "timeout_at": int(chain["timeout_at"]),
            },
            "user_request": user_request,
            "tool_results": tool_results,
            "constraints": {
                "allowed_outputs": ["followup_jobs", "final_answer"],
                "no_claims_of_direct_file_access": True,
                "prefer_minimal_jobs": True,
            },
        }

        if constraint_violation:
            llm_input["constraint_violation"] = constraint_violation

        # Create new agent_plan job
        llm_job_id = str(uuid.uuid4())
        created = now_iso()

        payload = {
            "kind": self.agent_plan_kind,
            "params": {
                "input": llm_input
            },
            "_chain_hint": {
                "chain_id": chain_id,
                "root_job_id": chain["root_job_id"],
                "depth": int(chain["depth"]) + 1,
                "role": "llm_step"
            }
        }

        from core.models import Job

        job = Job(
            id=llm_job_id,
            task_id=chain["root_job_id"],
            payload=payload,
            status="pending",
            result=None,
            retry_count=0,
            idempotency_key=f"chain:{chain_id}:agent_plan:{int(chain['depth'])}",
            priority="normal",
            timeout_seconds=300,
            depends_on=[],
            created_at=created,
            updated_at=created,
        )

        self.storage.create_job(job)

        # Update routing
        self.chain_index.put(llm_job_id, {
            "chain_id": chain_id,
            "role": "llm_step",
            "root_job_id": chain["root_job_id"],
            "parent_llm_job_id": chain.get("last_llm_job_id"),
            "depth": int(chain["depth"]) + 1,
        })

        # Update chain state
        chain["last_llm_job_id"] = llm_job_id
        chain["status"] = "WAITING_LLM"
        self.save_chain(chain)

        if self.logger:
            self.logger.info(f"[chain:{chain_id}] created next agent_plan job: {llm_job_id}")

        return llm_job_id

    def close_chain(self, *, chain_id: str, final_answer: Dict[str, Any]) -> None:
        """Mark chain as DONE with final answer."""
        chain = self.load_chain(chain_id)
        if not chain:
            return
        
        if chain.get("status") in ("DONE", "FAILED"):
            return

        chain["status"] = "DONE"
        chain["final_answer"] = final_answer
        chain["failed_reason"] = None
        self.save_chain(chain)

        if self.logger:
            self.logger.info(f"[chain:{chain_id}] DONE")
    
    def fail_chain(self, *, chain_id: str, reason: str) -> None:
        """Mark chain as FAILED with reason."""
        chain = self.load_chain(chain_id)
        if not chain:
            return
        
        if chain.get("status") in ("DONE", "FAILED"):
            return

        chain["status"] = "FAILED"
        chain["failed_reason"] = reason
        self.save_chain(chain)

        if self.logger:
            self.logger.warning(f"[chain:{chain_id}] FAILED: {reason}")
