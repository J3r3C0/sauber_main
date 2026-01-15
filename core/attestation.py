from __future__ import annotations
import json
import hashlib
import time
import os
from typing import Any, Dict, List, Optional, Tuple

def compute_capability_hash(caps: List[str]) -> str:
    """Stable SHA256 over sorted capability list."""
    if not caps:
        return "sha256:none"
    canonical = json.dumps(sorted(caps), separators=(',', ':'), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

def evaluate_attestation(node_record: Dict[str, Any], current: Optional[Dict[str, Any]], now_utc: str) -> Tuple[str, List[Dict[str, Any]], Optional[str]]:
    """
    Evaluate current attestation against node history.
    Returns: (status, events_to_log, health_hint)
    """
    history = node_record.get("attestation", {})
    if not current:
        # Backward compatibility for nodes without attestation data
        if not history:
             return "MISSING", [], None
        return history.get("status", "MISSING"), [], None

    events = []
    
    # Extract signals
    current_build = current.get("build_id", "unknown")
    current_cap_hash = current.get("capability_hash", "none")
    current_runtime = current.get("runtime", {})
    
    # 1. First Seen
    if not history.get("first_seen"):
        events.append({
            "event": "ATTESTATION_FIRST_SEEN",
            "data": {
                "build": current_build,
                "cap_prefix": current_cap_hash[:8]
            }
        })
        history["first_seen"] = {
            "ts_utc": now_utc,
            "build_id": current_build,
            "capability_hash": current_cap_hash,
            "runtime": current_runtime
        }
        history["status"] = "OK"
        history["drift_count"] = 0
        history["spoof_count"] = 0
        node_record["attestation"] = history
        return "OK", events, None

    # 2. Check for Drift (Comparison against FIRST SEEN as per v2.5.1)
    baseline = history["first_seen"]
    has_drift = (current_build != baseline.get("build_id")) or (current_cap_hash != baseline.get("capability_hash"))
    
    status = "OK"
    health_hint = None
    
    if has_drift:
        status = "DRIFT"
        health_hint = "YELLOW"
        history["drift_count"] = history.get("drift_count", 0) + 1
        events.append({
            "event": "ATTESTATION_DRIFT",
            "data": {
                "old_build": baseline.get("build_id"),
                "new_build": current_build,
                "old_cap": baseline.get("capability_hash")[:8],
                "new_cap": current_cap_hash[:8]
            }
        })

    # 3. Spoof Detection (Flip-Flop)
    # Threshold: ≥3 changes in window (SHERATAN_ATTESTATION_SPOOF_THRESHOLD or 3)
    last = history.get("last_seen", {})
    if last and last.get("capability_hash") and last.get("capability_hash") != current_cap_hash:
        # Detected a change between heartbeats
        history["spoof_count"] = history.get("spoof_count", 0) + 1
        threshold = int(os.environ.get("SHERATAN_ATTESTATION_SPOOF_THRESHOLD", "3"))
        if history["spoof_count"] >= threshold:
            status = "SPOOF_SUSPECT"
            health_hint = "YELLOW"
            events.append({
                "event": "ATTESTATION_SPOOF_SUSPECT",
                "data": {
                    "node_id": node_record.get("node_id"),
                    "spoof_count": history["spoof_count"]
                }
            })

    # Update state
    history["status"] = status
    history["last_seen"] = {
        "ts_utc": now_utc,
        "build_id": current_build,
        "capability_hash": current_cap_hash
    }
    history["last_change_utc"] = now_utc if has_drift else history.get("last_change_utc")
    node_record["attestation"] = history
    
    # Apply health hint if it makes the current state worse
    if health_hint == "YELLOW" and node_record.get("health", "GREEN") == "GREEN":
        node_record["health"] = "YELLOW"
        
    return status, events, health_hint
