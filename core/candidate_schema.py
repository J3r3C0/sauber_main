"""
Candidate Schema for MCTS-Light Selection

Every candidate MUST contain these fields before being passed to MCTS selection.
This ensures stable logging, selection, and policy updates.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict


@dataclass
class Candidate:
    """
    Structured candidate for MCTS-Light selection.
    
    Required fields:
    - action_id: Stable identifier for this specific action instance
    - type: Action type (ROUTE, RETRY, REWRITE, FALLBACK, etc.)
    - mode: simulate or execute
    - params: Action-specific parameters
    - risk_gate: Hard filter (False = candidate is blocked)
    - risk_penalty: Soft penalty for UCB calculation
    - cost_estimate: Estimated cost
    - latency_estimate_ms: Estimated latency
    - prior_key: Key for lookup in priors.json
    """
    
    action_id: str
    type: str  # ROUTE, EXECUTE, RETRY, REWRITE, FALLBACK, QUARANTINE, SKIP, ABORT
    mode: str  # simulate | execute
    params: Dict[str, Any]
    risk_gate: bool
    risk_penalty: float = 0.0
    cost_estimate: float = 0.0
    latency_estimate_ms: float = 0.0
    prior_key: Optional[str] = None
    
    def __post_init__(self):
        """Auto-generate prior_key if not provided"""
        if self.prior_key is None:
            # Build prior_key from type + params subtype
            subtype = self.params.get("subtype", "")
            self.prior_key = f"{self.type}:{subtype}" if subtype else self.type
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for MCTS selection"""
        return asdict(self)


def validate_candidates(candidates: List[Dict[str, Any]]) -> List[Candidate]:
    """
    Validate and convert candidate dicts to Candidate objects.
    
    Raises ValueError if any candidate is missing required fields.
    """
    validated = []
    
    for i, cand in enumerate(candidates):
        try:
            # Check required fields
            required = ["action_id", "type", "mode", "params", "risk_gate"]
            missing = [f for f in required if f not in cand]
            if missing:
                raise ValueError(f"Candidate {i} missing required fields: {missing}")
            
            # Create Candidate object (fills defaults)
            candidate = Candidate(
                action_id=cand["action_id"],
                type=cand["type"],
                mode=cand["mode"],
                params=cand["params"],
                risk_gate=cand["risk_gate"],
                risk_penalty=cand.get("risk_penalty", 0.0),
                cost_estimate=cand.get("cost_estimate", 0.0),
                latency_estimate_ms=cand.get("latency_estimate_ms", 0.0),
                prior_key=cand.get("prior_key")
            )
            
            validated.append(candidate)
            
        except Exception as e:
            raise ValueError(f"Invalid candidate {i}: {e}")
    
    return validated


def candidates_to_dicts(candidates: List[Candidate]) -> List[Dict[str, Any]]:
    """Convert Candidate objects back to dicts for MCTS"""
    return [c.to_dict() for c in candidates]
