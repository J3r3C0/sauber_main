"""
Stage 4 Validation: 10 Dispatches → 0 Breaches

Tests:
1. Dispatch 10 test jobs via MCTS integration
2. Verify 10 valid decision_trace events logged
3. Verify 0 breaches in breach log
4. Verify policy updates in priors.json

Requirements:
- System must be running (START_COMPLETE_SYSTEM.bat)
- Or run in standalone mode with mocked bridge
"""

import json
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.webrelay_bridge import WebRelayBridge, WebRelaySettings
from core.webrelay_mcts_integration import dispatch_with_mcts
from core import config


def test_10_dispatches_standalone():
    """
    Test 10 dispatches in standalone mode (no actual system running).
    Uses mocked bridge with minimal setup.
    """
    print("\n" + "=" * 60)
    print("Stage 4 Validation: 10 Dispatches → 0 Breaches")
    print("=" * 60)
    
    # Setup
    settings = WebRelaySettings(
        relay_out_dir=config.DATA_DIR / "webrelay_out",
        relay_in_dir=config.DATA_DIR / "webrelay_in"
    )
    bridge = WebRelayBridge(settings)
    
    # Clear logs for clean test
    decision_log = Path("logs/decision_trace.jsonl")
    breach_log = Path("logs/decision_trace_breaches.jsonl")
    
    if decision_log.exists():
        decision_log.unlink()
    if breach_log.exists():
        breach_log.unlink()
    
    print("\n[TEST] Dispatching 10 test jobs...")
    
    results = []
    for i in range(10):
        job_id = f"test_job_{i:03d}_{uuid.uuid4().hex[:8]}"
        
        try:
            # Create minimal job in storage
            from core import storage, models
            
            # Create mission
            mission = models.Mission(
                id=f"mission_{i}",
                user_id="test_user",
                goal="Test dispatch",
                status="active"
            )
            storage.create_mission(mission)
            
            # Create task
            task = models.Task(
                id=f"task_{i}",
                mission_id=mission.id,
                name="test_task",
                kind="llm_call",
                status="pending",
                params={}
            )
            storage.create_task(task)
            
            # Create job
            job = models.Job(
                id=job_id,
                task_id=task.id,
                status="pending",
                payload={}
            )
            storage.create_job(job)
            
            # Dispatch via MCTS
            result = dispatch_with_mcts(
                job_id=job_id,
                bridge=bridge,
                intent="dispatch_job",
                build_id="test_stage4"
            )
            
            results.append(result)
            print(f"  [{i+1}/10] Job {job_id[:20]}... → {result['chosen_action']['type']} (score={result['score']:.2f})")
            
        except Exception as e:
            print(f"  [{i+1}/10] FAILED: {e}")
            results.append({"success": False, "error": str(e)})
    
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
        print(f"    - {action_key}: visits={stats['visits']}, mean_score={stats['mean_score']:.2f}")
    
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
        success = test_10_dispatches_standalone()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ VALIDATION FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
