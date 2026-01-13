"""
Stage 4 Simplified Test: Decision Trace Logging

Tests MCTS decision tracing without full job dispatch.
Focuses on:
1. Candidate building
2. MCTS selection
3. Decision trace logging
4. Policy updates
5. 0 breaches
"""

import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.candidate_schema import Candidate, candidates_to_dicts
from core.mcts_light import mcts
from core.decision_trace import trace_logger
from core.scoring import compute_score_v1


def test_decision_trace_logging():
    """Test decision trace logging with 10 simulated decisions"""
    print("\n" + "=" * 60)
    print("Stage 4 Simplified Test: Decision Trace Logging")
    print("=" * 60)
    
    # Clear logs
    decision_log = Path("logs/decision_trace.jsonl")
    breach_log = Path("logs/decision_trace_breaches.jsonl")
    
    if decision_log.exists():
        decision_log.unlink()
    if breach_log.exists():
        breach_log.unlink()
    
    print("\n[TEST] Logging 10 decision traces...")
    
    for i in range(10):
        trace_id = str(uuid.uuid4())
        job_id = f"test_job_{i:03d}"
        
        # 1. Build candidates
        candidates = [
            Candidate(
                action_id=f"route_webrelay_{i}",
                type="ROUTE",
                mode="execute",
                params={"target": "webrelay"},
                risk_gate=True,
                risk_penalty=0.1,
                cost_estimate=1.0,
                latency_estimate_ms=2000
            ),
            Candidate(
                action_id=f"skip_{i}",
                type="SKIP",
                mode="simulate",
                params={},
                risk_gate=False,
                risk_penalty=1.0,
                cost_estimate=0.0,
                latency_estimate_ms=0
            )
        ]
        
        candidate_dicts = candidates_to_dicts(candidates)
        
        # 2. MCTS selection
        chosen_dict, scored_dicts = mcts.select_action("dispatch_job", candidate_dicts)
        
        # 3. Simulate execution
        latency_ms = 1500 + (i * 100)  # Vary latency
        result_status = "success" if i % 5 != 0 else "failed"  # 20% failure rate
        
        # 4. Calculate score
        score_breakdown = compute_score_v1(
            success=1.0 if result_status == "success" else 0.0,
            quality=0.8,
            reliability=0.9,
            latency_ms=latency_ms,
            cost=chosen_dict.get("cost_estimate", 0.0),
            risk=chosen_dict.get("risk_penalty", 0.0),
            latency_p50=500,
            latency_p95=2000,
            cost_p50=1.0,
            cost_p95=10.0
        )
        
        # 5. Log decision trace
        try:
            node_id = trace_logger.log_node(
                trace_id=trace_id,
                intent="dispatch_job",
                build_id="test_stage4",
                state={
                    "context_refs": [f"job:{job_id}"],
                    "constraints": {
                        "budget_remaining": 100.0,
                        "time_remaining_ms": 30000,
                        "readonly": False,
                        "risk_level": "low"
                    }
                },
                action={
                    "action_id": chosen_dict["action_id"],
                    "type": chosen_dict["type"],
                    "mode": chosen_dict["mode"],
                    "params": chosen_dict["params"],
                    "select_score": chosen_dict["select_score"],
                    "risk_gate": chosen_dict["risk_gate"]
                },
                result={
                    "status": result_status,
                    "metrics": {
                        "latency_ms": latency_ms,
                        "cost": chosen_dict.get("cost_estimate", 0.0),
                        "tokens": 0,
                        "retries": 0,
                        "risk": chosen_dict.get("risk_penalty", 0.0),
                        "quality": 0.8
                    },
                    "score": score_breakdown["score"],
                    "error": None if result_status == "success" else {"code": "TEST_FAILURE", "message": "Simulated failure"},
                    "artifacts": [f"job_result:{job_id}"]
                },
                job_id=job_id,
                depth=0
            )
            
            # 6. Update policy
            mcts.update_policy("dispatch_job", chosen_dict["prior_key"], score_breakdown["score"])
            
            print(f"  [{i+1}/10] {chosen_dict['type']:8s} → {result_status:8s} (score={score_breakdown['score']:.2f}, node_id={node_id[:8]}...)")
            
        except ValueError as e:
            print(f"  [{i+1}/10] BREACH: {e}")
    
    # Verify logs
    print("\n[VERIFY] Checking logs...")
    
    # 1. Check decision_trace.jsonl
    if not decision_log.exists():
        print("  ✗ decision_trace.jsonl not found")
        return False
    
    with open(decision_log) as f:
        decision_lines = f.readlines()
    
    print(f"  ✓ decision_trace.jsonl: {len(decision_lines)} events")
    
    # Validate each event
    valid_count = 0
    for i, line in enumerate(decision_lines):
        try:
            event = json.loads(line)
            assert event["schema_version"] == "decision_trace_v1"
            assert "node_id" in event
            assert "intent" in event
            assert event["intent"] == "dispatch_job"
            valid_count += 1
        except Exception as e:
            print(f"  ✗ Invalid event at line {i+1}: {e}")
            return False
    
    print(f"  ✓ All {valid_count} events are schema-valid")
    
    # 2. Check breach log
    breach_count = 0
    if breach_log.exists():
        with open(breach_log) as f:
            breach_lines = f.readlines()
            breach_count = len(breach_lines)
            if breach_count > 0:
                print(f"\n  Breaches found:")
                for line in breach_lines:
                    breach = json.loads(line)
                    print(f"    - {breach['error']['message']} at {breach['error']['path']}")
    
    if breach_count > 0:
        print(f"  ✗ {breach_count} breaches found (expected 0)")
        return False
    else:
        print(f"  ✓ 0 breaches (breach log clean)")
    
    # 3. Check priors.json updates
    priors_path = Path("policies/priors.json")
    if not priors_path.exists():
        print("  ✗ priors.json not found")
        return False
    
    with open(priors_path) as f:
        priors = json.load(f)
    
    if "dispatch_job" not in priors:
        print("  ✗ No 'dispatch_job' intent in priors")
        return False
    
    dispatch_priors = priors["dispatch_job"]
    print(f"  ✓ priors.json updated: {len(dispatch_priors)} actions learned")
    
    for action_key, stats in dispatch_priors.items():
        print(f"    - {action_key:20s}: visits={stats['visits']:2d}, mean_score={stats['mean_score']:6.2f}")
    
    # Summary
    print("\n" + "=" * 60)
    print("✓ STAGE 4 VALIDATION PASSED")
    print("=" * 60)
    print(f"  - {valid_count} valid decision traces logged")
    print(f"  - 0 schema breaches")
    print(f"  - {len(dispatch_priors)} actions in policy")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    try:
        success = test_decision_trace_logging()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ VALIDATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
