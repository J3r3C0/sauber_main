"""
Schema Mapping: Core Job ↔ Offgrid Job

This module defines the transformation logic between Core's job schema
and Offgrid's job schema for the Job Dispatch integration.
"""

from typing import Dict, Any, Optional
from . import models


# Core Job Schema → Offgrid Job Schema
def core_to_offgrid_job(job: models.Job, task: models.Task, mission: models.Mission) -> Dict[str, Any]:
    """
    Convert Core Job to Offgrid Job format for Broker auction.
    
    Args:
        job: Core Job object
        task: Parent Task object
        mission: Parent Mission object
    
    Returns:
        Offgrid job spec dictionary
    
    Example:
        Core Job:
        {
            "id": "job-123",
            "task_id": "task-abc",
            "payload": {"prompt": "Analyze this code"},
            "status": "pending"
        }
        
        Offgrid Job:
        {
            "job_id": "job-123",
            "type": "compute",
            "size": 0.25,  # compute_tokens_m
            "latency_ms": 5000,
            "constraints": {
                "max_latency_ms": 5000,
                "min_mesh_health": true
            },
            "meta": {
                "mission_id": "mission-xyz",
                "task_id": "task-abc",
                "kind": "llm_call"
            }
        }
    """
    
    # Infer resource type from task kind
    kind = task.kind or "llm_call"
    
    # Map kind to Offgrid resource type
    resource_type_map = {
        "llm_call": "compute",
        "agent_plan": "compute",
        "list_files": "compute",
        "read_file": "storage",
        "write_file": "storage",
        "rewrite_file": "storage",
    }
    resource_type = resource_type_map.get(kind, "compute")
    
    # Estimate compute size (tokens) from payload
    size = estimate_compute_size(job.payload, kind)
    
    # Extract constraints from job/task params
    constraints = extract_constraints(job.payload, task.params)
    
    return {
        "job_id": job.id,
        "type": resource_type,
        "size": size,
        "latency_ms": constraints.get("max_latency_ms", 5000),
        "constraints": constraints,
        "meta": {
            "mission_id": mission.id,
            "task_id": task.id,
            "kind": kind,
            "core_version": "v2"
        }
    }


# Offgrid Result → Core Result
def offgrid_to_core_result(offgrid_result: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert Offgrid job result to Core result format.
    
    Args:
        offgrid_result: Result from Offgrid Host
    
    Returns:
        Core-compatible result dictionary
    
    Example:
        Offgrid Result:
        {
            "ok": true,
            "receipt": {
                "job_id": "job-123",
                "node_id": "node-A",
                "metrics": {"compute_tokens_m": 0.25, "latency_ms": 1234}
            },
            "output": "Analysis complete: found 5 issues"
        }
        
        Core Result:
        {
            "ok": true,
            "action": "text_result",
            "text": "Analysis complete: found 5 issues",
            "offgrid_receipt": {...},
            "host": "http://127.0.0.1:8081",
            "metrics": {...}
        }
    """
    
    return {
        "ok": offgrid_result.get("ok", True),
        "action": "text_result",  # Default action for simple results
        "text": offgrid_result.get("output", ""),
        "offgrid_receipt": offgrid_result.get("receipt"),
        "host": offgrid_result.get("host"),
        "metrics": offgrid_result.get("receipt", {}).get("metrics", {})
    }


# Helper functions
def estimate_compute_size(payload: Dict[str, Any], kind: str) -> float:
    """
    Estimate compute size (in compute_tokens_m) from job payload.
    
    Rules:
    - llm_call: estimate from prompt length (rough: 1 token ≈ 4 chars)
    - agent_plan: fixed 0.5 tokens
    - list_files: fixed 0.01 tokens
    - read_file: fixed 0.05 tokens
    - write_file: estimate from content length
    """
    
    if kind == "llm_call" or kind == "agent_plan":
        prompt = payload.get("prompt", "")
        if isinstance(prompt, str):
            # Rough estimate: 1 token ≈ 4 characters
            tokens = len(prompt) / 4.0
            # Convert to millions
            return max(0.001, tokens / 1_000_000)
        return 0.1  # Default
    
    elif kind == "list_files":
        return 0.01
    
    elif kind == "read_file":
        return 0.05
    
    elif kind in ("write_file", "rewrite_file"):
        content = payload.get("content", "")
        if isinstance(content, str):
            # Estimate from content size
            tokens = len(content) / 4.0
            return max(0.01, tokens / 1_000_000)
        return 0.05
    
    return 0.1  # Default fallback


def extract_constraints(payload: Dict[str, Any], task_params: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Extract Offgrid constraints from job payload and task params.
    
    Constraints:
    - max_latency_ms: Maximum acceptable latency
    - min_mesh_health: Require mesh_ok=true from hosts
    - preferred_via: Preferred transport (udp, ble, lora)
    """
    
    constraints = {
        "max_latency_ms": 5000,  # Default 5s
        "min_mesh_health": False,
    }
    
    # Override from task params
    if task_params:
        if "max_latency_ms" in task_params:
            constraints["max_latency_ms"] = task_params["max_latency_ms"]
        if "min_mesh_health" in task_params:
            constraints["min_mesh_health"] = task_params["min_mesh_health"]
        if "preferred_via" in task_params:
            constraints["preferred_via"] = task_params["preferred_via"]
    
    # Override from job payload (highest priority)
    if "max_latency_ms" in payload:
        constraints["max_latency_ms"] = payload["max_latency_ms"]
    if "min_mesh_health" in payload:
        constraints["min_mesh_health"] = payload["min_mesh_health"]
    if "preferred_via" in payload:
        constraints["preferred_via"] = payload["preferred_via"]
    
    return constraints
