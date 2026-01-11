from __future__ import annotations

import os
import time
from contextlib import contextmanager
from typing import Optional

import requests

# Kannst du in deiner docker-compose / .env setzen:
# SHERATAN_METRICS_URL=http://backend:8000/metrics/module-calls
METRICS_URL = os.getenv(
    "SHERATAN_METRICS_URL",
    "http://backend:8000/metrics/module-calls",
)


def record_module_call(
    source: str,
    target: str,
    duration_ms: float,
    status: str = "ok",
    correlation_id: Optional[str] = None,
) -> None:
    """
    Sendet ein Modulaufruf-Event an das Metrics-Backend.
    Fire-and-forget, blockiert niemals den Core.
    """
    payload = {
        "source": source,
        "target": target,
        "duration_ms": float(duration_ms),
        "status": status,
    }
    if correlation_id:
        payload["correlation_id"] = correlation_id

    try:
        # Fire-and-forget, Monitoring darf niemals den Core blockieren
        requests.post(METRICS_URL, json=payload, timeout=0.2)
    except Exception:
        # Fehler werden bewusst geschluckt
        pass


@contextmanager
def measured_call(
    source: str,
    target: str,
    correlation_id: Optional[str] = None,
):
    """
    Kontext-Manager, der Dauer und Status eines Modulaufrufs misst
    und automatisch an das Metrics-Backend schickt.
    
    Usage:
        with measured_call("core_v2.api", "lcp_actions"):
            # your code here
            process_lcp_actions()
    """
    start = time.perf_counter()
    status = "ok"
    try:
        yield
    except Exception:
        status = "error"
        raise
    finally:
        duration_ms = (time.perf_counter() - start) * 1000.0
        record_module_call(
            source=source,
            target=target,
            duration_ms=duration_ms,
            status=status,
            correlation_id=correlation_id,
        )
