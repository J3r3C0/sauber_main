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


import threading

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

    def _send():
        try:
            # Fire-and-forget, Monitoring darf niemals den Core blockieren
            # Use 127.0.0.1 instead of backend to avoid DNS issues if not configured
            url = METRICS_URL
            if "backend:8000" in url:
                url = url.replace("backend:8000", "127.0.0.1:8001")
            
            requests.post(url, json=payload, timeout=0.5)
        except Exception:
            pass

    # Truly fire-and-forget by using a thread
    thread = threading.Thread(target=_send, daemon=True)
    thread.start()


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
