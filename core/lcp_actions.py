# core/lcp_actions.py
"""
LCP (LLM Control Protocol) Actions Parser
Handles parsing of LLM responses for job chaining (Phase 9).
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class FollowupJobs:
    """Represents a request for follow-up jobs from LLM."""
    chain_id: str
    jobs: List[Dict[str, Any]]


@dataclass
class FinalAnswer:
    """Represents a final answer from LLM (chain complete)."""
    chain_id: str
    answer: Dict[str, Any]


def is_lcp_message(result: Dict[str, Any]) -> bool:
    """
    Return True if result looks like an LCP envelope (v1 or legacy).
    
    Supports:
    - v1: {lcp_version:'1', type:'followup_jobs'|'final_answer', ...}
    - legacy: {action:'create_followup_jobs', new_jobs:[...]}
    """
    if not isinstance(result, dict):
        return False
    
    # v1 format
    if result.get("lcp_version") == "1" and "type" in result:
        return True
    
    # legacy format
    if result.get("action") in ["create_followup_jobs", "analysis_result"]:
        return True
    
    return False


def parse_lcp(result: Dict[str, Any], *, default_chain_id: str) -> Tuple[Optional[FollowupJobs], Optional[FinalAnswer]]:
    """
    Parse LCP envelope from result.
    
    Returns (followup, final) where exactly one should be non-None.
    """
    if not is_lcp_message(result):
        return (None, None)
    
    # Get chain_id (with fallback)
    chain_id = result.get("chain_id") or result.get("chain", {}).get("chain_id") or default_chain_id
    
    # v1 followup_jobs
    if result.get("type") == "followup_jobs":
        jobs = result.get("jobs", [])
        normalized = normalize_job_specs(jobs)
        return (FollowupJobs(chain_id=chain_id, jobs=normalized), None)
    
    # v1 final_answer
    if result.get("type") == "final_answer":
        answer = result.get("answer", {})
        return (None, FinalAnswer(chain_id=chain_id, answer=answer))
    
    # legacy create_followup_jobs
    if result.get("action") == "create_followup_jobs":
        jobs = result.get("new_jobs", [])
        normalized = normalize_job_specs(jobs)
        return (FollowupJobs(chain_id=chain_id, jobs=normalized), None)
    
    # legacy analysis_result (treat as final)
    if result.get("action") == "analysis_result":
        return (None, FinalAnswer(chain_id=chain_id, answer=result))
    
    return (None, None)


def normalize_job_specs(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Ensure each spec has: {kind: str, params: dict}
    Drop invalid entries deterministically.
    """
    normalized = []
    for spec in jobs:
        if not isinstance(spec, dict):
            continue
        
        kind = spec.get("kind") or spec.get("name")
        if not kind:
            continue
        
        params = spec.get("params", {})
        if not isinstance(params, dict):
            params = {}
        
        normalized.append({
            "kind": kind,
            "params": params
        })
    
    return normalized


# Legacy LCPActionInterpreter class (kept for backward compatibility)
class LCPActionInterpreter:
    """
    Legacy LCP handler - kept for backward compatibility.
    Phase 9 uses parse_lcp() directly in Core.
    """
    
    def __init__(self, bridge):
        self.bridge = bridge
    
    def handle_job_result(self, job):
        """
        Handle job result - placeholder for compatibility.
        Phase 9: Actual LCP handling is done in Core's sync_job endpoint.
        """
        pass
