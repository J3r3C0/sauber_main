# core/self_diagnostics.py
from __future__ import annotations

import threading
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class DiagnosticConfig:
    check_interval_sec: int = 300  # 5 minutes
    persist_interval_sec: int = 60  # baselines persist throttle
    reflective_enabled: bool = False  # keep conservative for now


class SelfDiagnosticEngine:
    """
    Background self-diagnostic loop.
    - periodically samples system state and updates PerformanceBaselineTracker
    - can emit health reports (basic v1)
    - can be manually triggered for immediate check

    This is intentionally conservative:
    - no aggressive state transitions
    - no heavy log parsing (we add that in Step 2/HealthReporter later)
    """

    def __init__(
        self,
        *,
        state_machine: Any,
        baseline_tracker: Any,
        config: Optional[DiagnosticConfig] = None,
    ) -> None:
        self.state_machine = state_machine
        self.baseline_tracker = baseline_tracker
        self.config = config or DiagnosticConfig()

        self._stop_evt = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.RLock()

        self._latest_report: Optional[Dict[str, Any]] = None
        self._latest_run_ts: float = 0.0

        # minimal counters (we'll wire real sources later)
        self._counters = {
            "llm_calls_ok": 0,
            "llm_calls_total": 0,
            "jobs_ok": 0,
            "jobs_total": 0,
            "latency_ms_sum": 0.0,
            "latency_ms_count": 0,
            "state_transitions_total": 0,
        }

    # -------------------------
    # Lifecycle
    # -------------------------

    def start(self) -> None:
        with self._lock:
            if self._thread and self._thread.is_alive():
                return
            self._stop_evt.clear()
            self._thread = threading.Thread(target=self._loop, name="SelfDiagnosticEngine", daemon=True)
            self._thread.start()

    def stop(self, *, timeout: float = 2.0) -> None:
        self._stop_evt.set()
        t = self._thread
        if t:
            t.join(timeout=timeout)

    # -------------------------
    # External hooks (optional)
    # -------------------------

    def record_llm_call(self, ok: bool) -> None:
        with self._lock:
            self._counters["llm_calls_total"] += 1
            if ok:
                self._counters["llm_calls_ok"] += 1

    def record_job_result(self, ok: bool, *, latency_ms: Optional[float] = None) -> None:
        with self._lock:
            self._counters["jobs_total"] += 1
            if ok:
                self._counters["jobs_ok"] += 1
            if latency_ms is not None:
                self._counters["latency_ms_sum"] += float(latency_ms)
                self._counters["latency_ms_count"] += 1

    def record_state_transition(self) -> None:
        with self._lock:
            self._counters["state_transitions_total"] += 1

    # -------------------------
    # Public API
    # -------------------------

    def get_latest_report(self) -> Dict[str, Any]:
        with self._lock:
            if self._latest_report is None:
                return self._empty_report()
            return dict(self._latest_report)

    def run_diagnostic(self, diagnostic_type: str = "manual") -> Dict[str, Any]:
        # immediate run in request thread (small/fast)
        report = self._run_once(trigger=diagnostic_type)
        with self._lock:
            self._latest_report = report
            self._latest_run_ts = time.time()
        return report

    # -------------------------
    # Internals
    # -------------------------

    def _loop(self) -> None:
        # initial small delay to allow system startup
        time.sleep(0.5)
        while not self._stop_evt.is_set():
            try:
                report = self._run_once(trigger="scheduled")
                with self._lock:
                    self._latest_report = report
                    self._latest_run_ts = time.time()
            except Exception as e:
                # keep loop alive; report error
                with self._lock:
                    self._latest_report = {
                        "schema_version": "health_report_v1",
                        "report_id": str(uuid.uuid4()),
                        "timestamp": self._ts_utc(),
                        "system_state": self._safe_state(),
                        "health_score": 0.0,
                        "findings": [
                            {
                                "severity": "error",
                                "category": "self_diagnostic",
                                "message": "SelfDiagnosticEngine crashed during loop iteration",
                                "evidence": {"error": repr(e)},
                                "recommendation": "Check server logs; diagnostic loop exception",
                            }
                        ],
                    }
            # sleep with stop responsiveness
            self._stop_evt.wait(self.config.check_interval_sec)

    def _run_once(self, *, trigger: str) -> Dict[str, Any]:
        now = time.time()
        state = self._safe_state()

        # --- derive quick metrics from counters (v1) ---
        with self._lock:
            jobs_total = self._counters["jobs_total"]
            jobs_ok = self._counters["jobs_ok"]
            llm_total = self._counters["llm_calls_total"]
            llm_ok = self._counters["llm_calls_ok"]
            lat_n = self._counters["latency_ms_count"]
            lat_sum = self._counters["latency_ms_sum"]

        job_success_rate = (jobs_ok / jobs_total) if jobs_total > 0 else None
        llm_success_rate = (llm_ok / llm_total) if llm_total > 0 else None
        avg_latency_ms = (lat_sum / lat_n) if lat_n > 0 else None

        # state transition rate is not computed here yet (needs windowed deltas)
        # we still update a placeholder sample when we have data later
        # For now: store 0.0 so baseline exists (optional)
        state_transition_rate = 0.0

        # worker availability: unknown in v1 -> None
        worker_availability = None

        # --- feed baselines (only if values present) ---
        if job_success_rate is not None:
            self.baseline_tracker.update("job_success_rate", float(job_success_rate), ts=now)
        if avg_latency_ms is not None:
            self.baseline_tracker.update("avg_job_latency_ms", float(avg_latency_ms), ts=now)
        if llm_success_rate is not None:
            self.baseline_tracker.update("llm_call_success_rate", float(llm_success_rate), ts=now)

        # keep state_transition_rate always updated (optional, harmless)
        self.baseline_tracker.update("state_transition_rate", float(state_transition_rate), ts=now)

        # only update if known
        if worker_availability is not None:
            self.baseline_tracker.update("worker_availability", float(worker_availability), ts=now)

        # persist throttled
        self.baseline_tracker.maybe_persist(
            min_interval_sec=self.config.persist_interval_sec,
            recompute=True,
        )

        # --- compute a simple health score v1 ---
        health_score = self._health_score_v1(
            job_success_rate=job_success_rate,
            llm_success_rate=llm_success_rate,
            avg_latency_ms=avg_latency_ms,
            state=state,
        )

        findings = []
        if job_success_rate is not None and job_success_rate < 0.8:
            findings.append({
                "severity": "warning",
                "category": "jobs",
                "message": "Low job success rate detected",
                "evidence": {"job_success_rate": job_success_rate, "jobs_total": jobs_total},
                "recommendation": "Inspect recent job failures; consider DEGRADED policy if persistent",
            })
        if llm_success_rate is not None and llm_success_rate < 0.8:
            findings.append({
                "severity": "warning",
                "category": "llm",
                "message": "Low LLM call success rate detected",
                "evidence": {"llm_call_success_rate": llm_success_rate, "llm_calls_total": llm_total},
                "recommendation": "Check WebRelay connectivity; consider fallback routing (Phase C)",
            })
        if avg_latency_ms is not None and avg_latency_ms > 5000:
            findings.append({
                "severity": "warning",
                "category": "performance",
                "message": "High average latency detected",
                "evidence": {"avg_job_latency_ms": avg_latency_ms},
                "recommendation": "Check worker saturation; investigate slow I/O or blocking calls",
            })

        report = {
            "schema_version": "health_report_v1",
            "report_id": str(uuid.uuid4()),
            "timestamp": self._ts_utc(),
            "trigger": trigger,
            "system_state": state,
            "health_score": health_score,
            "findings": findings,
            "baselines_path": "runtime/performance_baselines.json",
        }

        # conservative reflective usage: disabled by default
        if self.config.reflective_enabled and trigger in ("scheduled", "manual"):
            self._maybe_enter_reflective(report)

        return report

    def _maybe_enter_reflective(self, report: Dict[str, Any]) -> None:
        # Only enter reflective if something is wrong; keep conservative.
        try:
            if report.get("health_score", 1.0) < 0.7:
                self.state_machine.transition(
                    "REFLECTIVE",
                    reason="Health score below threshold",
                    actor="diagnostic_engine",
                    meta={"health_score": report.get("health_score"), "report_id": report.get("report_id")},
                )
        except Exception:
            # do not crash diagnostics if transition fails
            return

    def _health_score_v1(
        self,
        *,
        job_success_rate: Optional[float],
        llm_success_rate: Optional[float],
        avg_latency_ms: Optional[float],
        state: str,
    ) -> float:
        # Start with 1.0 and subtract penalties.
        score = 1.0

        if state in ("DEGRADED", "RECOVERY"):
            score -= 0.15

        if job_success_rate is not None:
            if job_success_rate < 0.9:
                score -= (0.9 - job_success_rate) * 1.5  # up to ~0.15
            if job_success_rate < 0.8:
                score -= 0.10

        if llm_success_rate is not None:
            if llm_success_rate < 0.9:
                score -= (0.9 - llm_success_rate) * 1.0
            if llm_success_rate < 0.8:
                score -= 0.08

        if avg_latency_ms is not None:
            # penalize above 2s
            if avg_latency_ms > 2000:
                score -= min(0.15, (avg_latency_ms - 2000) / 20000)  # max -0.15

        # clamp
        if score < 0.0:
            score = 0.0
        if score > 1.0:
            score = 1.0
        return float(score)

    def _safe_state(self) -> str:
        # Try to be compatible with different state_machine APIs.
        for attr in ("get_state", "current_state", "state"):
            try:
                v = getattr(self.state_machine, attr, None)
                if callable(v):
                    s = v()
                elif v is not None:
                    s = v
                else:
                    continue
                return str(s)
            except Exception:
                continue
        return "UNKNOWN"

    def _empty_report(self) -> Dict[str, Any]:
        return {
            "schema_version": "health_report_v1",
            "report_id": str(uuid.uuid4()),
            "timestamp": self._ts_utc(),
            "system_state": self._safe_state(),
            "health_score": 1.0,
            "findings": [],
        }

    def _ts_utc(self) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
