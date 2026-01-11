from dataclasses import asdict
from .pipeline import run_gates_v1, final_decision
from .config import default_gate_config

def run_all_gates(job: dict) -> dict:
    """
    Main entry point for running all safety gates on a job proposal.
    Wraps the pipeline for use by the Gatekeeper.
    """
    reports = run_gates_v1(job, default_gate_config)
    overall, next_action = final_decision(reports)
    
    return {
        "overall": overall,
        "next_action": next_action,
        "reports": [asdict(r) for r in reports],
        "issues": [
            {
                "gate_id": r.gate_id,
                "status": r.status,
                "reasons": [asdict(rs) for rs in r.reasons]
            }
            for r in reports if r.status != "PASS"
        ]
    }
