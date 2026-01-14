# core/performance_baseline.py
from __future__ import annotations

import json
import math
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class WindowSpec:
    key: str
    seconds: int


DEFAULT_WINDOWS: List[WindowSpec] = [
    WindowSpec("1h", 60 * 60),
    WindowSpec("24h", 24 * 60 * 60),
    WindowSpec("7d", 7 * 24 * 60 * 60),
]


DEFAULT_METRICS: List[str] = [
    "job_success_rate",        # 0..1
    "avg_job_latency_ms",      # >=0
    "state_transition_rate",   # events/hour or events/min (define later)
    "llm_call_success_rate",   # 0..1
    "worker_availability",     # 0..1
]


class PerformanceBaselineTracker:
    """
    Tracks time-series samples per metric and computes rolling-window baselines
    (mean/stddev) for standard windows (1h, 24h, 7d).

    Persistence:
      - JSON file written atomically to runtime/performance_baselines.json

    Important:
      - This tracker does NOT decide what values mean.
      - Feed it with tracker.update(metric, value) from the system (Step 3).
    """

    def __init__(
        self,
        *,
        runtime_dir: str | Path = "runtime",
        filename: str = "performance_baselines.json",
        windows: Optional[List[WindowSpec]] = None,
        metrics: Optional[List[str]] = None,
        max_samples_per_metric: int = 20000,
    ) -> None:
        self._lock = threading.RLock()
        self._windows = windows or list(DEFAULT_WINDOWS)
        self._metrics = metrics or list(DEFAULT_METRICS)
        self._max_samples = int(max_samples_per_metric)

        self._runtime_dir = Path(runtime_dir)
        self._path = self._runtime_dir / filename

        # samples: metric -> list[(ts, value)]
        self._samples: Dict[str, List[Tuple[float, float]]] = {m: [] for m in self._metrics}

        # computed: metric -> window -> stats
        self._baselines: Dict[str, Dict[str, dict]] = {m: {} for m in self._metrics}

        self._last_persist_ts: float = 0.0
        self._dirty: bool = False

        self._ensure_runtime_dir()
        self._load_if_exists()

    # ---------------------------
    # Public API
    # ---------------------------

    def update(self, metric: str, value: float, *, ts: Optional[float] = None) -> None:
        """Add a sample for a metric (ts defaults to now)."""
        if metric not in self._samples:
            # allow dynamic metrics if needed
            with self._lock:
                self._samples.setdefault(metric, [])
                self._baselines.setdefault(metric, {})

        t = float(ts if ts is not None else time.time())
        v = float(value)

        with self._lock:
            buf = self._samples[metric]
            buf.append((t, v))

            # cap memory
            if len(buf) > self._max_samples:
                # drop oldest chunk (fast)
                drop = len(buf) - self._max_samples
                del buf[:drop]

            self._dirty = True

    def recompute(self, *, now: Optional[float] = None) -> None:
        """Recompute baselines for all metrics + windows."""
        n = float(now if now is not None else time.time())

        with self._lock:
            for metric, buf in self._samples.items():
                self._baselines[metric] = {}
                for w in self._windows:
                    stats = self._compute_window(buf, w.seconds, now=n)
                    self._baselines[metric][w.key] = stats

    def get_all_baselines(self, *, recompute: bool = True) -> dict:
        """Return a snapshot dict suitable for API output."""
        with self._lock:
            if recompute:
                self.recompute()

            return {
                "schema_version": "performance_baselines_v1",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "windows": [{"key": w.key, "seconds": w.seconds} for w in self._windows],
                "metrics": list(self._baselines.keys()),
                "baselines": self._baselines,
            }

    def persist(self, *, recompute: bool = True) -> None:
        """Atomically write baselines to disk."""
        payload = self.get_all_baselines(recompute=recompute)

        with self._lock:
            self._ensure_runtime_dir()
            self._atomic_write_json(self._path, payload)
            self._last_persist_ts = time.time()
            self._dirty = False

    def maybe_persist(self, *, min_interval_sec: int = 60, recompute: bool = True) -> bool:
        """Persist if dirty and interval passed. Returns True if persisted."""
        with self._lock:
            if not self._dirty:
                return False
            if (time.time() - self._last_persist_ts) < float(min_interval_sec):
                return False

        self.persist(recompute=recompute)
        return True

    # ---------------------------
    # Internals
    # ---------------------------

    def _compute_window(
        self,
        buf: List[Tuple[float, float]],
        window_seconds: int,
        *,
        now: float,
    ) -> dict:
        cutoff = now - float(window_seconds)
        # Filter recent samples (buf is chronological)
        # We'll scan from end backwards until cutoff for speed on large buffers.
        values: List[float] = []
        for t, v in reversed(buf):
            if t < cutoff:
                break
            values.append(v)

        values.reverse()
        n = len(values)
        if n == 0:
            return {
                "count": 0,
                "mean": None,
                "stddev": None,
                "min": None,
                "max": None,
                "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
            }

        mean = sum(values) / n
        # population stddev (stable enough for baselines)
        var = sum((x - mean) ** 2 for x in values) / n
        std = math.sqrt(var)

        return {
            "count": n,
            "mean": mean,
            "stddev": std,
            "min": min(values),
            "max": max(values),
            "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        }

    def _ensure_runtime_dir(self) -> None:
        self._runtime_dir.mkdir(parents=True, exist_ok=True)

    def _load_if_exists(self) -> None:
        if not self._path.exists():
            return
        try:
            with self._path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            # We keep this loader conservative: we only load known shape if present.
            baselines = data.get("baselines")
            if isinstance(baselines, dict):
                with self._lock:
                    for metric, win_map in baselines.items():
                        if isinstance(win_map, dict):
                            self._baselines.setdefault(metric, {})
                            self._baselines[metric].update(win_map)
        except Exception:
            # If file is corrupt, we ignore (Step 3 diagnostics can flag this later)
            return

    def _atomic_write_json(self, path: Path, payload: dict) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
        with tmp.open("w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
