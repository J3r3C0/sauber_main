import json
import time
import threading
import urllib.request
import urllib.error
import logging
from typing import Optional

from core.config import MeshConfig
from .mesh_registry import WorkerRegistry

logger = logging.getLogger("mesh.prober")

def ping(url: str, timeout_s: float) -> tuple[bool, float]:
    """Pings a worker endpoint and returns (success, latency_ms)."""
    start = time.time()
    try:
        # urllib is zero-dependency and stable cross-platform
        # We append /health by convention
        health_url = url.rstrip("/")
        if not health_url.endswith("/health"):
            health_url += "/health"
            
        req = urllib.request.Request(health_url, method="GET")
        with urllib.request.urlopen(req, timeout=timeout_s) as resp:
            ok = (200 <= resp.status < 300)
    except (urllib.error.URLError, TimeoutError, Exception) as e:
        # Silently fail, record_probe_result handles thresholds
        ok = False
        
    latency_ms = (time.time() - start) * 1000.0
    return ok, latency_ms

class HealthProber:
    """
    Background worker that actively probes all registered workers.
    Ensures 'last_seen_ts' and 'is_offline' are kept up-to-date even 
    if no jobs are currently running.
    """
    def __init__(self, registry: WorkerRegistry, interval_s: Optional[int] = None):
        self.registry = registry
        self.interval_s = interval_s or MeshConfig.PROBER_INTERVAL_S
        self.timeout_s = MeshConfig.PROBER_TIMEOUT_S
        self.fail_threshold = MeshConfig.PROBER_FAIL_THRESHOLD
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self, daemon: bool = True):
        """Starts the probing loop in a background thread."""
        if self._thread and self._thread.is_alive():
            return
            
        self._stop.clear()
        self._thread = threading.Thread(target=self.run_forever, daemon=daemon, name="MeshHealthProber")
        self._thread.start()
        logger.info(f"HealthProber started (interval={self.interval_s}s, threshold={self.fail_threshold})")

    def stop(self):
        """Signals the prober to stop."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5.0)
            logger.info("HealthProber stopped")

    def run_forever(self):
        """Internal loop."""
        while not self._stop.is_set():
            try:
                self.tick()
            except Exception as e:
                logger.error(f"Error during prober tick: {e}")
            
            # Use wait() on the event for responsive shutdown
            self._stop.wait(self.interval_s)

    def tick(self):
        """A single pass over all workers."""
        # Get a snapshot of current workers
        worker_ids = list(self.registry.workers.keys())
        
        for wid in worker_ids:
            if self._stop.is_set():
                break
                
            worker = self.registry.get_worker(wid)
            if not worker or not worker.endpoint:
                continue
                
            ok, lat_ms = ping(worker.endpoint, self.timeout_s)
            
            # Update registry (handles locking internally)
            self.registry.record_probe_result(
                worker_id=wid,
                latency_ms=lat_ms,
                success=ok,
                fail_threshold=self.fail_threshold
            )
            
            if not ok:
                logger.warning(f"mesh.probe fail id='{wid}' endpoint='{worker.endpoint}'")

if __name__ == "__main__":
    # Simple standalone check if needed
    # (Requires a running registry or mock)
    pass
