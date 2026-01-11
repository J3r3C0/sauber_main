"""
Gatekeeper - Watches narrative/ and runs Gates (G0-G4)

Responsibilities:
1. Watch runtime/narrative/proposal_*.json
2. Run Gates (G0-G4)
3. Write runtime/proofed/gate_report_*.json
4. If PASS -> runtime/input/job_*.json (direct emit!)
5. If FAIL -> runtime/proofed/audit_request_*.json
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
NARRATIVE_DIR = RUNTIME_DIR / "narrative"
PROOFED_DIR = RUNTIME_DIR / "proofed"
INPUT_DIR = RUNTIME_DIR / "input"

# Initialize Ledger
logger = RealityLogger("gatekeeper")

# Ensure directories exist
PROOFED_DIR.mkdir(parents=True, exist_ok=True)
INPUT_DIR.mkdir(parents=True, exist_ok=True)


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


async def process_proposal(proposal_path: Path):
    """Process a single proposal through gates."""
    filename = proposal_path.name
    # Robust Job ID extraction
    job_id = filename.replace(".json", "").replace("proposal_", "").replace("analysis_", "")
    
    try:
        # Load proposal
        content = proposal_path.read_text(encoding="utf-8")
        if not content.strip():
            return
            
        proposal = json.loads(content)
        
        # If the file already contains a job_id (like from analyzer), use it
        if "job_id" in proposal:
            job_id = proposal["job_id"]
            
        print(f"[gatekeeper] [SCAN] Scanning: {filename} (Extracted ID: {job_id})")
        
        # Log: GATE_STARTED
        logger.log(
            event="GATE_STARTED",
            job_id=job_id,
            zone="narrative",
            artifact_path=proposal_path
        )
        
        # Run Gates
        from .gates.gate_runner import run_all_gates
        gate_bundle = run_all_gates(proposal)
        
        # Decision based on gates
        overall = gate_bundle.get("overall", "FAIL")
        next_action = gate_bundle.get("next_action", "QUARANTINE")
        
        # Log: GATE_PASS or GATE_FAIL
        logger.log(
            event="GATE_PASS" if overall == "PASS" else "GATE_FAIL",
            job_id=job_id,
            zone="proofed",
            artifact_path=None, # Report written below
            meta={"reason_codes": gate_bundle.get("issues", [])}
        )
        
        if overall == "PASS" and next_action == "ALLOW":
            # Direct emit to input/
            job_data = {
                **proposal,
                "job_id": job_id,
                "provenance": {
                    **proposal.get("provenance", {}),
                    "gated_at": utc_now_iso(),
                    "gate_status": "PASS"
                }
            }
            input_path = INPUT_DIR / f"job_{job_id}.json"
            input_path.write_text(json.dumps(job_data, indent=2), encoding="utf-8")
            print(f"[gatekeeper] [PASS] [{job_id}] -> Emitted to input/")
            
        elif next_action == "REQUIRE_LLM2":
            # Create audit request
            from .llm2_audit import emit_audit_request
            audit_req_path = emit_audit_request(
                job_id=job_id,
                job_proposal=proposal,
                gate_bundle=gate_bundle,
                reason=f"Gates {overall}, requires LLM2 audit"
            )
            # Move to proofed/
            new_path = PROOFED_DIR / audit_req_path.name
            if new_path.exists():
                new_path.unlink() # Clean up existing
            audit_req_path.rename(new_path)
            
            print(f"[gatekeeper] [AUDIT] AUDIT REQUIRED [{job_id}] -> Proofed zone")
            
        else:
            print(f"[gatekeeper] [REJECT] REJECTED [{job_id}] -> Staying in narrative")
        
        # Archive proposal (rename to .processed)
        processed_path = proposal_path.with_suffix(".processed")
        if processed_path.exists():
            processed_path.unlink()
        proposal_path.rename(processed_path)
        
    except Exception as e:
        print(f"[gatekeeper] [ERROR] CRITICAL ERROR for {filename}: {e}")


async def gatekeeper_loop():
    """Main loop - watch narrative/ for proposals."""
    print("[gatekeeper] Starting Gatekeeper...")
    print(f"[gatekeeper] Watching: {NARRATIVE_DIR} (*.json)")
    
    while True:
        try:
            # Find unprocessed files
            proposals = list(NARRATIVE_DIR.glob("*.json"))
            
            if proposals:
                print(f"[gatekeeper] Found {len(proposals)} new files in narrative.")
                for proposal_path in proposals:
                    await process_proposal(proposal_path)
            
            # Wait before next check
            await asyncio.sleep(5)
            
        except Exception as e:
            print(f"[gatekeeper] [ERROR] Loop error: {e}")
            await asyncio.sleep(10)


if __name__ == "__main__":
    print("=" * 60)
    print("SHERATAN GATEKEEPER - Gates (G0-G4)")
    print("=" * 60)
    asyncio.run(gatekeeper_loop())
