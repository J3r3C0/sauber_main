# core/anomaly_detector.py
from __future__ import annotations

import time
import uuid
import threading
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class Anomaly:
    anomaly_id: str
    timestamp: str
    severity: str          # "info" | "warning" | "error"
    category: str          # "state_transition" | "jobs" | "llm" | "performance" | "resource"
    message: str
    evidence: Dict[str, Any]
    recommendation: str


class AnomalyDetector:
    """
    Detects anomalies based on:
    - baseline deviation (mean/stddev) from PerformanceBaselineTracker output
    - simple heuristics (thresholds) as a backstop if baseline empty

    Keeps anomalies in-memory (v1). Persistence can be added later (JSONL).
    """

    def __init__(self, *, max_anomalies: int = 500) -> None:
        self._lock = threading.RLock()
        self._max = int(max_anomalies)
        self._items: List[Anomaly] = []

        # default per-metric z-score thresholds
        self._z = {
            "job_success_rate": 2.5,       # low is bad
            "llm_call_success_rate": 2.5,  # low is bad
            "avg_job_latency_ms": 3.0,     # high is bad
            "state_transition_rate": 3.0,  # high is suspicious (flapping)
        }

        # fallback thresholds if no baseline yet
        self._fallback = {
            "job_success_rate_min": 0.80,
            "llm_call_success_rate_min": 0.80,
            "avg_job_latency_ms_max": 5000,
            "state_transition_rate_max": 10.0,  # depends on your unit later
        }

    # ----------------------------
    # Public API
    # ----------------------------

    def detect(
        self,
        *,
        baselines_snapshot: Dict[str, Any],
        current_metrics: Dict[str, float],
        window: str = "1h",
        system_state: str = "UNKNOWN",
    ) -> List[Dict[str, Any]]:
        """
        Returns a list of anomalies (as dicts) detected for this check,
        and stores them in memory.
        """
        found: List[Anomaly] = []
        bmap = (baselines_snapshot or {}).get("baselines", {})

        for metric, value in current_metrics.items():
            # If we have baseline stats, use z-score logic.
            stats = None
            try:
                stats = bmap.get(metric, {}).get(window)
            except Exception:
                stats = None

            if stats and stats.get("count", 0) and stats.get("mean") is not None and stats.get("stddev") is not None:
                a = self._detect_by_zscore(metric, value, stats, system_state=system_state, window=window)
                if a:
                    found.append(a)
            else:
                # fallback heuristic
                a = self._detect_by_threshold(metric, value, system_state=system_state, window=window)
                if a:
                    found.append(a)

        if found:
            with self._lock:
                for a in found:
                    self._items.append(a)
                # cap
                if len(self._items) > self._max:
                    self._items = self._items[-self._max :]

        return [self._as_dict(a) for a in found]

    def get_anomalies(self, *, window: str = "1h", limit: int = 100) -> Dict[str, Any]:
        with self._lock:
            items = self._items[-int(limit):]
            return {
                "schema_version": "anomalies_v1",
                "timestamp": self._ts_utc(),
                "window": window,
                "count": len(items),
                "anomalies": [self._as_dict(a) for a in items],
            }

    # ----------------------------
    # Internals
    # ----------------------------

    def _detect_by_zscore(self, metric: str, value: float, stats: Dict[str, Any], *, system_state: str, window: str) -> Optional[Anomaly]:
        mean = float(stats["mean"])
        std = float(stats["stddev"])
        count = int(stats.get("count", 0))
        if std <= 0.0 or count < 5:
            return None

        z = (float(value) - mean) / std
        thr = float(self._z.get(metric, 3.0))

        # direction rules
        is_bad = False
        direction = "any"
        if metric in ("job_success_rate", "llm_call_success_rate"):
            direction = "low"
            is_bad = z <= -thr
        elif metric in ("avg_job_latency_ms", "state_transition_rate"):
            direction = "high"
            is_bad = z >= thr
        else:
            is_bad = abs(z) >= thr

        if not is_bad:
            return None

        severity = "warning"
        if abs(z) >= (thr + 1.5):
            severity = "error"

        msg = f"Baseline deviation detected for {metric} ({direction})"
        rec = self._recommendation(metric)

        return Anomaly(
            anomaly_id=str(uuid.uuid4()),
            timestamp=self._ts_utc(),
            severity=severity,
            category=self._category(metric),
            message=msg,
            evidence={
                "metric": metric,
                "value": float(value),
                "mean": mean,
                "stddev": std,
                "z_score": float(z),
                "threshold": thr,
                "window": window,
                "system_state": system_state,
                "baseline_count": count,
            },
            recommendation=rec,
        )

    def _detect_by_threshold(self, metric: str, value: float, *, system_state: str, window: str) -> Optional[Anomaly]:
        v = float(value)

        if metric == "job_success_rate" and v < self._fallback["job_success_rate_min"]:
            return self._mk("warning", metric, v, system_state, window, "Job success rate below threshold")
        if metric == "llm_call_success_rate" and v < self._fallback["llm_call_success_rate_min"]:
            return self._mk("warning", metric, v, system_state, window, "LLM call success rate below threshold")
        if metric == "avg_job_latency_ms" and v > self._fallback["avg_job_latency_ms_max"]:
            return self._mk("warning", metric, v, system_state, window, "Average job latency above threshold")
        if metric == "state_transition_rate" and v > self._fallback["state_transition_rate_max"]:
            return self._mk("info", metric, v, system_state, window, "State transition rate unusually high")

        return None

    def _mk(self, severity: str, metric: str, value: float, system_state: str, window: str, msg: str) -> Anomaly:
        return Anomaly(
            anomaly_id=str(uuid.uuid4()),
            timestamp=self._ts_utc(),
            severity=severity,
            category=self._category(metric),
            message=msg,
            evidence={
                "metric": metric,
                "value": float(value),
                "window": window,
                "system_state": system_state,
                "mode": "threshold",
            },
            recommendation=self._recommendation(metric),
        )

    def _category(self, metric: str) -> str:
        if metric in ("job_success_rate",):
            return "jobs"
        if metric in ("llm_call_success_rate",):
            return "llm"
        if metric in ("avg_job_latency_ms",):
            return "performance"
        if metric in ("state_transition_rate",):
            return "state_transition"
        return "performance"

    def _recommendation(self, metric: str) -> str:
        if metric == "job_success_rate":
            return "Inspect recent job failures; check worker logs and retry policy."
        if metric == "llm_call_success_rate":
            return "Check WebRelay connectivity; consider fallback routing (Phase C)."
        if metric == "avg_job_latency_ms":
            return "Check worker saturation; investigate blocking calls and I/O latency."
        if metric == "state_transition_rate":
            return "Possible state flapping; review recent transitions and underlying triggers."
        return "Review evidence and correlate with recent system changes."

    def _as_dict(self, a: Anomaly) -> Dict[str, Any]:
        return {
            "anomaly_id": a.anomaly_id,
            "timestamp": a.timestamp,
            "severity": a.severity,
            "category": a.category,
            "message": a.message,
            "evidence": a.evidence,
            "recommendation": a.recommendation,
        }

    def _ts_utc(self) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
