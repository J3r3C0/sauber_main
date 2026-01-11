"""
Final Decision - Handles Audit Reports and Re-Gating

Responsibilities:
1. Watch runtime/proofed/audit_report_*.json
2. If ALLOW -> apply patches -> re-gate
3. If re-gate PASS -> runtime/input/job_*.json
4. If FAIL -> runtime/quarantine/failed_*.json
"""
import asyncio
import json
from pathlib import Path
from typing import Dict, Any
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment
_this_dir = Path(__file__).parent
env_path = _this_dir / ".env"
load_dotenv(dotenv_path=env_path)

from .event_logger import RealityLogger

# Paths
_this_dir = Path(__file__).parent
_project_root = (_this_dir / ".." / "..").resolve()
RUNTIME_DIR = _project_root / "runtime"
PROOFED_DIR = RUNTIME_DIR / "proofed"
INPUT_DIR = RUNTIME_DIR / "input"
QUARANTINE_DIR = RUNTIME_DIR / "quarantine"
NARRATIVE_DIR = RUNTIME_DIR / "narrative"

# Initialize Ledger
logger = RealityLogger("final")

# Ensure directories exist
QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


async def process_audit_report(report_path: Path):
    """Process audit report and make final decision."""
    job_id = report_path.stem.replace("audit_report_", "")
    
    try:
        # Load audit report
        audit_report = json.loads(report_path.read_text(encoding="utf-8"))
        decision = audit_report.get("decision", "PAUSE")
        
        print(f"[final_decision] Processing audit for {job_id}: {decision}")
        
        if decision == "ALLOW":
            # Load original proposal
            proposal_path = NARRATIVE_DIR / f"proposal_{job_id}.processed"
            if not proposal_path.exists():
                proposal_path = NARRATIVE_DIR / f"proposal_{job_id}.json"
            
            if not proposal_path.exists():
                print(f"[final_decision] ERROR: Proposal not found for {job_id}")
                return
            
            proposal = json.loads(proposal_path.read_text(encoding="utf-8"))
            
            # Apply patches if any
            fix_suggestions = audit_report.get("fix_suggestions", [])
            if fix_suggestions:
                from .patch_applicator import apply_patch
                from .patch_validator import validate_patch
                
                try:
                    # Validate patches
                    for patch_op in fix_suggestions:
                        validate_patch(patch_op)
                    
                    # Apply patches
                    patched_job = apply_patch(proposal, fix_suggestions)
                    print(f"[final_decision] Applied {len(fix_suggestions)} patches")
                    
                    # Ensure provenance for re-gating (G0)
                    patched_job.setdefault("provenance", {})["source_zone"] = "narrative"
                    
                    # Re-run gates
                    from .gates.gate_runner import run_all_gates
                    gate_bundle = run_all_gates(patched_job)
                    
                    if gate_bundle.get("overall") == "PASS":
                        # Emit to input/
                        job_data = {
                            **patched_job,
                            "provenance": {
                                **patched_job.get("provenance", {}),
                                "audit_decision": "ALLOW",
                                "patched_at": utc_now_iso(),
                                "re_gated_at": utc_now_iso()
                            }
                        }
                        input_path = INPUT_DIR / f"job_{job_id}.json"
                        input_path.write_text(json.dumps(job_data, indent=2), encoding="utf-8")
                        print(f"[final_decision] [ALLOW] ALLOW + Re-Gate PASS -> {input_path.name}")
                        
                        # Log: JOB_EMITTED_TO_INPUT
                        logger.log(
                            event="JOB_EMITTED_TO_INPUT",
                            job_id=job_id,
                            zone="input",
                            artifact_path=input_path,
                            meta={"patched": True}
                        )
                    else:
                        # Re-gate failed
                        quarantine_path = QUARANTINE_DIR / f"failed_{job_id}.json"
                        quarantine_data = {
                            "job_id": job_id,
                            "reason": "Re-gate failed after patch",
                            "gate_bundle": gate_bundle,
                            "audit_report": audit_report,
                            "quarantined_at": utc_now_iso()
                        }
                        quarantine_path.write_text(json.dumps(quarantine_data, indent=2), encoding="utf-8")
                        print(f"[final_decision] [FAIL] Re-Gate FAIL -> {quarantine_path.name}")
                        
                        # Log: JOB_QUARANTINED
                        logger.log(
                            event="JOB_QUARANTINED",
                            job_id=job_id,
                            zone="quarantine",
                            artifact_path=quarantine_path,
                            meta={"reason": quarantine_data["reason"]}
                        )
                
                except ValueError as e:
                    # Illegal patch
                    quarantine_path = QUARANTINE_DIR / f"failed_{job_id}.json"
                    quarantine_data = {
                        "job_id": job_id,
                        "reason": f"Illegal patch: {e}",
                        "audit_report": audit_report,
                        "quarantined_at": utc_now_iso()
                    }
                    quarantine_path.write_text(json.dumps(quarantine_data, indent=2), encoding="utf-8")
                    print(f"[final_decision] [ILLEGAL] Illegal patch -> {quarantine_path.name}")
            
            else:
                # No patches, direct emit (shouldn't happen, but handle it)
                # Ensure provenance for re-gating (G0)
                proposal.setdefault("provenance", {})["source_zone"] = "narrative"
                
                job_data = {
                    **proposal,
                    "provenance": {
                        **proposal.get("provenance", {}),
                        "audit_decision": "ALLOW",
                        "approved_at": utc_now_iso()
                    }
                }
                input_path = INPUT_DIR / f"job_{job_id}.json"
                input_path.write_text(json.dumps(job_data, indent=2), encoding="utf-8")
                print(f"[final_decision] [ALLOW] ALLOW (no patches) -> {input_path.name}")
                
                # Log: JOB_EMITTED_TO_INPUT
                logger.log(
                    event="JOB_EMITTED_TO_INPUT",
                    job_id=job_id,
                    zone="input",
                    artifact_path=input_path,
                    meta={"patched": False}
                )
        
        else:
            # PAUSE or MANUAL_REVIEW
            quarantine_path = QUARANTINE_DIR / f"failed_{job_id}.json"
            quarantine_data = {
                "job_id": job_id,
                "reason": f"Audit decision: {decision}",
                "audit_report": audit_report,
                "quarantined_at": utc_now_iso()
            }
            quarantine_path.write_text(json.dumps(quarantine_data, indent=2), encoding="utf-8")
            print(f"[final_decision] [PAUSE] {decision} -> {quarantine_path.name}")
        
        # Archive report
        processed_path = report_path.with_suffix(".processed")
        report_path.rename(processed_path)
        
    except Exception as e:
        print(f"[final_decision] ERROR processing {job_id}: {e}")


async def final_decision_loop():
    """Main loop - watch proofed/ for audit reports."""
    print("[final_decision] Starting Final Decision...")
    print(f"[final_decision] Watching: {PROOFED_DIR}")
    iteration = 0
    
    while True:
        try:
            iteration += 1
            # Find unprocessed audit reports
            reports = list(PROOFED_DIR.glob("audit_report_*.json"))
            
            if reports:
                print(f"[final_decision] Found {len(reports)} new audit reports.")
                for report_path in reports:
                    await process_audit_report(report_path)
            
            # Heartbeat every 10 iterations (~50s)
            if iteration % 10 == 0:
                print(f"[final_decision] [HB] Heartbeat | Listening for audit reports in {PROOFED_DIR.name}")

            # Wait before next check
            await asyncio.sleep(5)
            
        except Exception as e:
            print(f"[final_decision] [ERROR] Loop error: {e}")
            await asyncio.sleep(10)


if __name__ == "__main__":
    print("=" * 60)
    print("SHERATAN FINAL DECISION - Patch + Re-Gate")
    print("=" * 60)
    asyncio.run(final_decision_loop())
