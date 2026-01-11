# mesh_registry.py
import json
import os
import time
import logging
from pathlib import Path
from typing import Dict, List, Optional
from pydantic import BaseModel
from core.utils.atomic_io import atomic_write_json, json_lock
from core.config import MeshConfig

logger = logging.getLogger("mesh.registry")

class WorkerCapability(BaseModel):
    kind: str
    cost: int  # Token cost per job

class WorkerStats(BaseModel):
    latency_ms_ema: float = 750.0  # Default 50% of 1500ms cap
    success_ema: float = 0.85      # Conservative neutral prior
    n: int = 0                     # Observation count
    last_seen_ts: float = 0.0
    consecutive_failures: int = 0
    is_offline: bool = False
    cooldown_until: float = 0.0    # Timestamp until worker is blocked
    active_jobs: int = 0           # In-flight job count

class WorkerInfo(BaseModel):
    worker_id: str
    capabilities: List[WorkerCapability]
    status: str = "online"
    last_seen: float = 0.0          # Legend field, stats.last_seen_ts is moving truth
    endpoint: Optional[str] = None  # For remote mesh workers if needed
    stats: WorkerStats = WorkerStats()
    meta: Dict = {}

class WorkerRegistry:
    def __init__(self, storage_path: Path = Path("workers.json"), max_inflight: int = 3):
        self.storage_path = storage_path
        self.workers: Dict[str, WorkerInfo] = {}
        self.max_inflight = max_inflight # Per-worker limit
        self.load()

    def load(self):
        """Loads worker registry from storage with .bak fallback and safety guards."""
        if not self.storage_path.exists():
            self.workers = {}
            return

        # Note: Callers should handle json_lock if multi-process safety is needed.
        # We don't lock here to avoid deadlocks in nested calls like record_probe_result.
        try:
            self._load_from_path(self.storage_path)
        except (json.JSONDecodeError, Exception) as e:
            bak_path = self.storage_path.with_suffix(".json.bak")
            if bak_path.exists():
                logger.warning(f"Failed to load {self.storage_path}, falling back to {bak_path}: {e}")
                try:
                    self._load_from_path(bak_path)
                    # Self-heal primary file
                    self.save()
                except Exception as e2:
                    logger.error(f"Failed to load backup {bak_path}: {e2}")
                    self.workers = {}
            else:
                logger.error(f"Failed to load {self.storage_path} and no backup found: {e}")
                self.workers = {}

    def _load_from_path(self, path: Path):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Basic validation
            if not isinstance(data, dict):
                raise ValueError("Registry data must be a dictionary")
            
            new_workers = {}
            for wid, wdata in data.items():
                try:
                    new_workers[wid] = WorkerInfo(**wdata)
                except Exception as e:
                    logger.warning(f"Skipping invalid worker record {wid}: {e}")
            self.workers = new_workers

    def save(self):
        data = {k: v.model_dump() for k, v in self.workers.items()}
        atomic_write_json(str(self.storage_path), data)

    def register(self, worker: WorkerInfo):
        with json_lock(str(self.storage_path)):
            self.load() # Reload under lock
            worker.last_seen = time.time()
            self.workers[worker.worker_id] = worker
            self.save()

    def get_worker(self, worker_id: str) -> Optional[WorkerInfo]:
        return self.workers.get(worker_id)

    def find_workers_for_kind(self, kind: str) -> List[WorkerInfo]:
        """Finds online workers for a kind, filtering out those not seen in STALE_TTL."""
        now = time.time()
        
        return [
            w for w in self.workers.values()
            if any(c.kind == kind for c in w.capabilities) 
            and w.status == "online"
            and (now - w.last_seen) < MeshConfig.STALE_TTL
        ]

    def heartbeat(self, worker_id: str):
        with json_lock(str(self.storage_path)):
            self.load() # Reload under lock
            if worker_id in self.workers:
                self.workers[worker_id].last_seen = time.time()
                self.workers[worker_id].status = "online"
                self.save()

    def _update_ema(self, stats: WorkerStats, latency_ms: float, success: bool, alpha: float = 0.2):
        """Internal helper to update EMA stats."""
        # Update Success EMA
        success_val = 1.0 if success else 0.0
        stats.success_ema = (alpha * success_val) + (1.0 - alpha) * stats.success_ema
        
        # Update Latency EMA (only on success to avoid skewing)
        if success:
            stats.latency_ms_ema = (alpha * latency_ms) + (1.0 - alpha) * stats.latency_ms_ema
        
        stats.n += 1
        stats.last_seen_ts = time.time()

    def record_worker_result(self, worker_id: str, latency_ms: float, success: bool):
        """Records a job result and updates EMA stats for the worker."""
        with json_lock(str(self.storage_path)):
            # Preserve consecutive_failures before reload
            prev_failures = 0
            if worker_id in self.workers:
                prev_failures = self.workers[worker_id].stats.consecutive_failures
            
            self.load() # Reload under lock
            if worker_id not in self.workers:
                return

            worker = self.workers[worker_id]
            self._update_ema(worker.stats, latency_ms, success)
            
            # Passive updates also reset failures
            if success:
                worker.stats.consecutive_failures = 0
                worker.stats.is_offline = False
            else:
                # Restore and increment for failures
                worker.stats.consecutive_failures = prev_failures + 1
                if worker.stats.consecutive_failures >= 3:
                    worker.stats.is_offline = True
                    worker.stats.cooldown_until = time.time() + 300
            
            # Decrement active jobs
            worker.stats.active_jobs = max(0, worker.stats.active_jobs - 1)
            
            worker.last_seen = worker.stats.last_seen_ts # Sync legacy field
            self.save()

    def record_probe_result(self, worker_id: str, latency_ms: float, success: bool, fail_threshold: int = 3):
        """Records a health probe result."""
        with json_lock(str(self.storage_path)):
            self.load()
            if worker_id not in self.workers:
                return
            
            worker = self.workers[worker_id]
            stats = worker.stats
            
            if success:
                self._update_ema(stats, latency_ms, True)
                stats.consecutive_failures = 0
                stats.is_offline = False
            else:
                stats.consecutive_failures += 1
                if stats.consecutive_failures >= fail_threshold:
                    stats.is_offline = True
                    # Trigger cooldown
                    stats.cooldown_until = time.time() + 300 # 5 min cooldown
            
            # Decrement active jobs (min 0)
            stats.active_jobs = max(0, stats.active_jobs - 1)
            
            worker.last_seen = stats.last_seen_ts
            self.save()

    def record_job_start(self, worker_id: str):
        """Track an in-flight job."""
        if worker_id in self.workers:
            self.workers[worker_id].stats.active_jobs += 1
            # We don't save immediately to minimize I/O on hot path

    def is_eligible(self, worker_id: str) -> bool:
        """Check if a worker is currently allowed to take jobs."""
        if worker_id not in self.workers:
            return False
        
        stats = self.workers[worker_id].stats
        now = time.time()
        
        # 1. Offline or Stale
        if stats.is_offline: return False
        if stats.last_seen_ts > 0 and (now - stats.last_seen_ts) > MeshConfig.STALE_TTL: return False
        
        # 2. Cooldown
        if stats.cooldown_until > now: return False
        
        # 3. Reliability Gate
        if stats.n >= MeshConfig.WARMUP_N and stats.success_ema < MeshConfig.REL_MIN: return False
        
        # 4. In-flight Limit
        if stats.active_jobs >= self.max_inflight: return False
        
        return True

    def get_best_worker(self, kind: str) -> Optional[WorkerInfo]:
        """Finds the best worker for a kind using a weighted score (Cost, Reliability, Latency)."""
        candidates = self.find_workers_for_kind(kind)
        if not candidates:
            return None

        # Config gates
        now = time.time()
        
        valid_candidates = []
        for w in candidates:
            if self.is_eligible(w.worker_id):
                valid_candidates.append(w)

        if not valid_candidates:
            logger.warning(f"mesh.select_worker kind='{kind}' result=NONE reason='All candidates filtered by gates'")
            return None

        # Optimization: if only one candidate remains after gates
        if len(valid_candidates) == 1:
            winner = valid_candidates[0]
            logger.info(f"mesh.select_worker kind='{kind}' winner='{winner.worker_id}' reason='Single valid candidate'")
            return winner

        # Scoring
        w_cost, w_rel, w_lat = MeshConfig.normalized_weights()
        min_cost = min(next(c.cost for c in w.capabilities if c.kind == kind) for w in valid_candidates)
        
        scored_candidates = []
        for w in valid_candidates:
            cost = next(c.cost for c in w.capabilities if c.kind == kind)
            cost_score = min_cost / cost if cost > 0 else 1.0
            lat_score = max(0.0, min(1.0, 1.0 - (w.stats.latency_ms_ema / MeshConfig.LAT_CAP_MS)))
            rel_score = max(0.0, min(1.0, w.stats.success_ema))
            
            total_score = (w_cost * cost_score) + (w_rel * rel_score) + (w_lat * lat_score)
            scored_candidates.append((total_score, cost_score, rel_score, lat_score, w))

        # Sort by total_score descending
        scored_candidates.sort(key=lambda x: x[0], reverse=True)
        winner = scored_candidates[0][4]
        
        # Logging Top 3 for observability
        top3_debug = []
        for s, cs, rs, ls, w in scored_candidates[:3]:
            top3_debug.append({
                "id": w.worker_id,
                "score": f"{s:.3f}",
                "metrics": {"c": f"{cs:.2f}", "r": f"{rs:.2f}", "l": f"{ls:.2f}"}
            })
        
        logger.info(f"mesh.select_worker kind='{kind}' winner='{winner.worker_id}' top3={json.dumps(top3_debug)}")
        return winner
