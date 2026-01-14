"""
Stage 4 Integration: MCTS-Light Decision Tracing in WebRelay Dispatch

This module provides a wrapper around WebRelayBridge.enqueue_job to:
1. Build candidate list (local/webrelay/api/skip)
2. Apply risk gates
3. Select via MCTS-Light
4. Measure outcome
5. Log decision trace
6. Update policy

Usage:
    from core.webrelay_mcts_integration import dispatch_with_mcts
    
    result = dispatch_with_mcts(
        job_id="job_123",
        bridge=webrelay_bridge,
        intent="dispatch_job",
        build_id="main"
    )
"""

import time
import uuid
from typing import Dict, Any, Optional
from pathlib import Path

from core.webrelay_bridge import WebRelayBridge
from core.mcts_light import mcts
from core.decision_trace import trace_logger
from core.candidate_schema import Candidate, validate_candidates, candidates_to_dicts
from core.scoring import compute_score_v1
from core.determinism import compute_input_hash, compute_output_hash


def normalize_trace_state(state: Optional[dict]) -> dict:
    """
    Ensure decision_trace_v1 schema requirements are met.
    In particular: state.constraints is required.
    """
    if state is None:
        state = {}
    s = dict(state)  # avoid mutating caller
    if "constraints" not in s or s["constraints"] is None:
        s["constraints"] = {}
    return s


def build_dispatch_candidates(
    job_id: str,
    bridge: WebRelayBridge,
    kind: str = "llm_call"
) -> list[Candidate]:
    """
    Build candidate list for job dispatch.
    
    Candidates:
    - ROUTE:worker_id (for each eligible worker from registry)
    - ROUTE:webrelay (if webrelay configured)
    - SKIP (fallback, always gated=False)
    """
    candidates = []
    
    # Candidate 1-N: Workers from registry
    if bridge.registry:
        workers = bridge.registry.find_workers_for_kind(kind)
        for worker in workers:
            is_eligible = bridge.registry.is_eligible(worker.worker_id)
            cost = next((c.cost for c in worker.capabilities if c.kind == kind), 0)
            
            candidates.append(Candidate(
                action_id=f"route_{worker.worker_id}_{job_id[:8]}",
                type="ROUTE",
                mode="execute",
                params={"target": "worker", "worker_id": worker.worker_id, "kind": kind},
                risk_gate=is_eligible,
                risk_penalty=0.0 if is_eligible else 0.5,
                cost_estimate=float(cost),
                latency_estimate_ms=worker.stats.latency_ms_ema
            ))
    
    # Candidate N+1: WebRelay (if configured)
    if bridge.settings and bridge.settings.relay_out_dir:
        candidates.append(Candidate(
            action_id=f"route_webrelay_{job_id[:8]}",
            type="ROUTE",
            mode="execute",
            params={"target": "webrelay"},
            risk_gate=True,
            risk_penalty=0.1,
            cost_estimate=1.0,
            latency_estimate_ms=2000
        ))
    
    # Candidate N+2: SKIP (always gated=False as fallback)
    candidates.append(Candidate(
        action_id=f"skip_{job_id[:8]}",
        type="SKIP",
        mode="simulate",
        params={},
        risk_gate=False,
        risk_penalty=1.0,
        cost_estimate=0.0,
        latency_estimate_ms=0
    ))
    
    return candidates


def dispatch_with_mcts(
    job_id: str,
    bridge: WebRelayBridge,
    intent: str = "dispatch_job",
    build_id: str = "main",
    kind: str = "llm_call"
) -> Dict[str, Any]:
    """
    Dispatch job with MCTS-Light selection and decision tracing.
    
    Returns:
        {
            "success": bool,
            "node_id": str,
            "chosen_action": dict,
            "score": float,
            "result": dict
        }
    """
    trace_id = str(uuid.uuid4())
    
    # 1. Build candidates
    candidates = build_dispatch_candidates(job_id, bridge, kind)
    candidate_dicts = candidates_to_dicts(candidates)
    
    # 2. MCTS selection
    chosen_dict, scored_dicts = mcts.select_action(intent, candidate_dicts)
    
    # 3. Execute chosen action
    start_time = time.time()
    
    try:
        if chosen_dict["type"] == "ROUTE":
            # Execute actual dispatch
            bridge.enqueue_job(job_id)
            result_status = "success"
            result_error = None
        elif chosen_dict["type"] == "SKIP":
            # Skipped
            result_status = "skipped"
            result_error = None
        else:
            result_status = "failed"
            result_error = {"code": "UNKNOWN_ACTION", "message": f"Unknown action type: {chosen_dict['type']}"}
    
    except Exception as e:
        result_status = "failed"
        result_error = {"code": "DISPATCH_ERROR", "message": str(e)}
    
    latency_ms = (time.time() - start_time) * 1000
    
    # 4. Determine cost/tokens (semantic cleanup)
    # Local workers: cost=0, tokens not measured
    # WebRelay/API: use actual cost/tokens if available
    actual_cost = 0.0  # Local dispatch has no cost
    actual_tokens = None  # Not measured for local dispatch
    
    # 5. Calculate score
    score_breakdown = compute_score_v1(
        success=1.0 if result_status == "success" else 0.0,
        quality=0.8,  # TODO: Measure actual quality
        reliability=0.9,  # TODO: Measure actual reliability
        latency_ms=latency_ms,
        cost=actual_cost,
        risk=chosen_dict.get("risk_penalty", 0.0),
        latency_p50=500,
        latency_p95=2000,
        cost_p50=1.0,
        cost_p95=10.0
    )
    
    # 6. Compute determinism hashes
    state_obj = {
        "context_refs": [f"job:{job_id}"],
        "constraints": {
            "budget_remaining": 100.0,
            "time_remaining_ms": 30000,
            "readonly": False,
            "risk_level": "low"
        }
    }
    
    action_obj = {
        "action_id": chosen_dict["action_id"],
        "type": chosen_dict["type"],
        "mode": chosen_dict["mode"],
        "params": chosen_dict["params"],
        "select_score": chosen_dict["select_score"],
        "risk_gate": chosen_dict["risk_gate"]
    }
    
    metrics_obj = {
        "latency_ms": latency_ms,
        "cost": actual_cost,
        "retries": 0,
        "risk": chosen_dict.get("risk_penalty", 0.0),
        "quality": 0.8
    }
    # Only include tokens if measured (not None)
    if actual_tokens is not None:
        metrics_obj["tokens"] = actual_tokens
    
    input_hash = compute_input_hash(
        job_id=job_id,
        intent=intent,
        action_type=action_obj["type"],
        action_params=action_obj["params"],
        state_constraints=state_obj["constraints"],
        state_context_refs=state_obj["context_refs"]
    )
    
    output_hash = compute_output_hash(
        status=result_status,
        score=score_breakdown["score"],
        metrics=metrics_obj,
        error_code=result_error["code"] if result_error else None,
        artifacts=[f"job_result:{job_id}"]
    )
    
    # 7. Log decision trace
    try:
        node_id = trace_logger.log_node(
            trace_id=trace_id,
            intent=intent,
            build_id=build_id,
            state=normalize_trace_state(state_obj),
            action=action_obj,
            result={
                "status": result_status,
                "metrics": metrics_obj,
                "score": score_breakdown["score"],
                "error": result_error,
                "artifacts": [f"job_result:{job_id}"],
                "determinism": {
                    "input_hash": input_hash,
                    "output_hash": output_hash
                }
            },
            job_id=job_id,
            depth=0
        )
    except ValueError as e:
        # Schema breach - logged to breach file
        print(f"[WARN] Decision trace schema breach: {e}")
        node_id = None
    
    # 8. Update policy
    if node_id:
        mcts.update_policy(intent, chosen_dict["prior_key"], score_breakdown["score"])
    
    return {
        "success": result_status == "success",
        "node_id": node_id,
        "chosen_action": chosen_dict,
        "score": score_breakdown["score"],
        "result": {
            "status": result_status,
            "error": result_error,
            "latency_ms": latency_ms
        }
    }
