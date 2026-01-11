import json
import asyncio
import httpx
import os
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional, Dict
from dotenv import load_dotenv

# Load environment
_this_dir = Path(__file__).parent
env_path = _this_dir / ".env"
load_dotenv(dotenv_path=env_path)

from .llm2_audit import audit_request_path, audit_report_path, _write_json, _read_json
from .event_logger import RealityLogger

# Configuration
WEB_RELAY_URL = "http://localhost:3001/api/llm/call"
logger = RealityLogger("auditor")
_this_dir = Path(__file__).parent
_project_root = (_this_dir / ".." / "..").resolve()
RUNTIME_DIR = _project_root / "runtime"
PROOFED_DIR = RUNTIME_DIR / "proofed"  # Audit requests/reports
FAILED_DIR = RUNTIME_DIR / "quarantine" / "auditor"  # Dead Letter Queue
CONTROL_DIR = RUNTIME_DIR / "control"  # For replay requests

# Retry Configuration
MAX_ATTEMPTS = 3
BACKOFF_SCHEDULE = [0, 60, 240]  # Exponential: 0s, 1m, 4m
MAX_CONCURRENT_AUDITS = 1
STALE_THRESHOLD_MINUTES = 30

# Ensure dirs exist
FAILED_DIR.mkdir(parents=True, exist_ok=True)
CONTROL_DIR.mkdir(parents=True, exist_ok=True)

AUDITOR_SYSTEM_PROMPT = """You are the SHERATAN AUDITOR & FIX-COACH [v2.0].
Your role is to analyze job proposals that have been flagged by Safety Gates (G0-G4) and provide high-fidelity remediation paths.

GATES OVERVIEW:
- G0: Flow Barrier (Source Zone validation)
- G1: Schema Integrity (LCP compliance)
- G2: Command Allowlist (Safe operation check)
- G3: Path Sandbox (Directory traversal & absolute path prevention)
- G4: Escalation Detection (Prevention of runaway autonomy)

DECISION HIERARCHY:
- ALLOW: The proposal is safe as-is (False Positive).
- MANUAL_REVIEW: High risk, human intervention required.
- PAUSE: Critical violation, no immediate fix possible.

FIX-COACH PROTOCOL:
1. RESPONSE: Strictly valid JSON.
2. schema:
   {
     "decision": "ALLOW" | "MANUAL_REVIEW" | "PAUSE",
     "severity": "LOW" | "MEDIUM" | "HIGH",
     "violations": [{"gate_id": string, "code": string, "why": string}],
     "fix_suggestions": [{"op": "replace", "path": "/params/path", "value": "...safe path..."}],
     "message_to_llm1": "A direct, coaching message explaining the safety boundary and how to fix it."
   }

3. MISSION: Help the SHERATAN AGENT (LLM1) achieve its goal within safety boundaries. Be technical, precise, and educational.
4. CRITICAL: Return ONLY the complete JSON object shown in schema above. Start with { and end with }. No markdown, no code blocks, no extra text.
"""

import re

def _extract_json(text: str) -> Optional[dict]:
    """Robustly extracts JSON from LLM response using outermost brace detection."""
    # 1. Try markdown blocks first
    for match in re.finditer(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL):
        try:
            candidate = match.group(1).strip()
            if candidate:
                return json.loads(candidate)
        except:
            continue
            
    # 2. Find all opening braces and find the longest balanced string
    # This is more robust than simple regex for nested structures
    best_parsed = None
    start_indices = [m.start() for m in re.finditer(r"{", text)]
    
    for start in start_indices:
        # Search from the end for the closing brace
        for end in range(len(text) - 1, start, -1):
            if text[end] == '}':
                candidate = text[start:end+1]
                try:
                    parsed = json.loads(candidate)
                    if isinstance(parsed, dict) and "decision" in parsed:
                        # If we find a valid one, we prefer the one that is largest
                        # (usually the main report vs echoes)
                        if not best_parsed or len(candidate) > len(json.dumps(best_parsed)):
                             best_parsed = parsed
                except:
                    continue
                    
    return best_parsed


def utc_now_iso() -> str:
    """Return current UTC time as ISO8601 string."""
    return datetime.now(timezone.utc).isoformat()


# 🔴 CRITICAL: Circuit Breaker to prevent LLM cost explosion
class AuditorCircuitBreaker:
    def __init__(self):
        self.failure_count = 0
        self.last_success = datetime.now(timezone.utc)
        self.circuit_open_until = None
    
    def should_attempt(self) -> bool:
        """Check if circuit allows attempts."""
        # Circuit open? Check if cooldown expired
        if self.circuit_open_until:
            if datetime.now(timezone.utc) < self.circuit_open_until:
                return False  # Circuit still OPEN
            else:
                # Reset circuit
                self.circuit_open_until = None
                self.failure_count = 0
        
        # After 5 failures in 10min -> Open circuit for 30min
        if self.failure_count >= 5:
            time_since_success = (datetime.now(timezone.utc) - self.last_success).total_seconds()
            if time_since_success < 600:  # 10 minutes
                self.circuit_open_until = datetime.now(timezone.utc) + timedelta(minutes=30)
                print(f"[auditor] 🔴 Circuit OPEN until {self.circuit_open_until}")
                return False
        
        return True
    
    def record_success(self):
        self.failure_count = 0
        self.last_success = datetime.now(timezone.utc)
    
    def record_failure(self):
        self.failure_count += 1


# Global circuit breaker instance
circuit_breaker = AuditorCircuitBreaker()


def should_retry(metadata: Dict) -> bool:
    """Check if we should retry this audit request."""
    attempts = metadata.get("attempts", 0)
    
    if attempts >= MAX_ATTEMPTS:
        return False
    
    # 🔴 Check circuit breaker
    if not circuit_breaker.should_attempt():
        return False
    
    next_retry_str = metadata.get("next_retry", "1970-01-01T00:00:00Z")
    try:
        next_retry = datetime.fromisoformat(next_retry_str)
        return datetime.now(timezone.utc) >= next_retry
    except:
        return True  # If parsing fails, allow retry


def update_retry_metadata(processing_path: Path, error: str):
    """Update processing file with retry metadata."""
    try:
        metadata = json.loads(processing_path.read_text(encoding="utf-8"))
    except:
        metadata = {"job_id": processing_path.stem.replace("audit_request_", "").replace(".processing", "")}
    
    attempts = metadata.get("attempts", 0) + 1
    metadata["attempts"] = attempts
    metadata["last_attempt"] = utc_now_iso()
    
    if attempts < MAX_ATTEMPTS:
        # 🔴 Exponential backoff
        backoff_seconds = BACKOFF_SCHEDULE[min(attempts, len(BACKOFF_SCHEDULE)-1)]
        next_retry = datetime.now(timezone.utc) + timedelta(seconds=backoff_seconds)
        metadata["next_retry"] = next_retry.isoformat()
    
    metadata.setdefault("errors", []).append({
        "attempt": attempts,
        "error": error,
        "at": utc_now_iso()
    })
    
    processing_path.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")


def move_to_dead_letter(processing_path: Path, reason: str):
    """Move failed audit to dead letter queue."""
    try:
        metadata = json.loads(processing_path.read_text(encoding="utf-8"))
    except:
        metadata = {"job_id": "unknown"}
    
    metadata["failed_at"] = utc_now_iso()
    metadata["fail_reason"] = reason
    
    job_id = metadata.get("job_id", "unknown")
    failed_path = FAILED_DIR / f"audit_failed_{job_id}.json"
    _write_json(failed_path, metadata)
    
    processing_path.unlink(missing_ok=True)
    print(f"[auditor] 💀 Moved {job_id} to dead letter: {reason}")


def reclaim_stale_processing():
    """Find .processing files older than threshold and reclaim or fail them."""
    for processing_path in PROOFED_DIR.glob("*.processing"):
        try:
            metadata = json.loads(processing_path.read_text(encoding="utf-8"))
            
            last_attempt_str = metadata.get("last_attempt", "1970-01-01T00:00:00Z")
            last_attempt = datetime.fromisoformat(last_attempt_str)
            age_minutes = (datetime.now(timezone.utc) - last_attempt).total_seconds() / 60
            
            if age_minutes > STALE_THRESHOLD_MINUTES:
                if metadata.get("attempts", 0) >= MAX_ATTEMPTS:
                    move_to_dead_letter(processing_path, "Max retries exceeded (stale)")
                else:
                    # Reset to pending (rename back to .json)
                    pending_path = processing_path.with_suffix(".json")
                    processing_path.rename(pending_path)
                    print(f"[auditor] [RECYCLE] Reclaimed stale processing: {pending_path.name}")
        except Exception as e:
            print(f"[auditor] WARN: Failed to reclaim {processing_path.name}: {e}")


def check_replay_requests():
    """Check for operator replay requests from dead letter."""
    for replay_file in CONTROL_DIR.glob("replay_*.json"):
        try:
            replay = json.loads(replay_file.read_text(encoding="utf-8"))
            job_id = replay.get("job_id")
            
            if not job_id:
                replay_file.unlink()
                continue
            
            # Move from failed/ back to pending
            failed_path = FAILED_DIR / f"audit_failed_{job_id}.json"
            if failed_path.exists():
                pending_path = PROOFED_DIR / f"audit_request_{job_id}.json"
                
                # Reset metadata
                metadata = json.loads(failed_path.read_text(encoding="utf-8"))
                metadata["attempts"] = 0
                metadata["replayed_by"] = replay.get("operator", "unknown")
                metadata["replayed_at"] = utc_now_iso()
                metadata["errors"] = []  # Clear error history
                
                _write_json(pending_path, metadata)
                failed_path.unlink()
                replay_file.rename(replay_file.with_suffix(".processed"))
                
                print(f"[auditor] 🔄 Replayed {job_id} from dead letter")
        except Exception as e:
            print(f"[auditor] WARN: Failed to process replay {replay_file.name}: {e}")

async def process_one_audit(request_path: Path):
    # Atomic claim: rename to .processing
    processing_path = request_path.with_suffix(".processing")
    try:
        request_path.rename(processing_path)
    except FileNotFoundError:
        return # Someone else got it

    try:
        # 1. Read and Validate Request
        try:
            req = _read_json(processing_path)
        except Exception as e:
            print(f"[auditor] ERR: JSON Parse error for {request_path.name}: {e}")
            processing_path.unlink(missing_ok=True)
            return

        # Basic Schema & Size Guard
        if req.get("schema") != "sheratan.llm2_audit_request.v1":
            print(f"[auditor] ERR: Invalid schema in {request_path.name}")
            processing_path.unlink()
            return
            
        job_id = req.get("job_id", "unknown")
        # Path Sanitization
        if not re.match(r"^[a-zA-Z0-9_\-]+$", str(job_id)) or len(str(job_id)) > 100:
            print(f"[auditor] ERR: Dangerous job_id: {job_id}")
            processing_path.unlink()
            return

        report_p = audit_report_path(job_id)
        if report_p.exists():
            print(f"[auditor] INFO: Report already exists for {job_id}, skipping.")
            processing_path.unlink()
            return

        print(f"[auditor] Processing audit for Job {job_id}...")
        
        # Log: AUDIT_STARTED
        logger.log(
            event="AUDIT_STARTED",
            job_id=job_id,
            zone="proofed",
            artifact_path=processing_path
        )
        
        # Get API key
        api_key = os.getenv("SHERATAN_API_KEY", "")
        if not api_key:
            print("[auditor] WARN: SHERATAN_API_KEY not found in environment!")
        else:
            print(f"[auditor] Using API key starting with '{api_key[:4]}...'")
        
        # Build prompt
        prompt = f"{AUDITOR_SYSTEM_PROMPT}\n\nAUDIT REQUEST:\n{json.dumps(req, indent=2)}"
        print(f"[auditor] Built prompt for {job_id} ({len(prompt)} chars)")
        
        report_data = None
        try:
            print(f"[auditor] Calling WebRelay at {WEB_RELAY_URL}...")
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(WEB_RELAY_URL, 
                    headers={"X-SHERATAN-KEY": api_key},
                    json={
                        "prompt": prompt,
                        "session_id": f"audit_{job_id}",
                        "llm_backend": "chatgpt"
                    }
                )
                
                print(f"[auditor] WebRelay responded with status {resp.status_code}")
                
                if resp.status_code != 200:
                    raise Exception(f"WebRelay failed ({resp.status_code}): {resp.text[:200]}")
                
                data = resp.json()
                answer = data.get("summary") or data.get("thought") or data.get("answer") or ""
                
                # Save raw response for debugging
                raw_response_path = PROOFED_DIR / f"audit_raw_response_{job_id}.txt"
                try:
                    raw_response_path.write_text(f"WebRelay Response Keys: {list(data.keys())}\n\nAnswer:\n{answer}", encoding="utf-8")
                except:
                    pass
                
                # 3. Robust Extraction & Validation
                report_data = _extract_json(answer)
                if not report_data or "decision" not in report_data:
                    print(f"[auditor] Raw answer preview: {answer[:1000]}")
                    raise Exception("LLM failed to return valid JSON report")

        except httpx.TimeoutException:
            raise Exception(f"WebRelay timeout after 60s for {job_id}")
        except Exception as e:
            # Re-raise to be caught by the outer error handler
            raise e

        # 4. Save & Enrich Report
        # Fail-Closed Decision Guard
        valid_decisions = {"ALLOW", "MANUAL_REVIEW", "PAUSE"}
        if report_data["decision"] not in valid_decisions:
            print(f"[auditor] WARN: Invalid decision '{report_data['decision']}', forcing PAUSE")
            report_data["decision"] = "PAUSE"

        # Enrich & Save
        report_data["job_id"] = job_id
        report_data["schema"] = "sheratan.llm2_audit_report.v1"
        report_data["created_at_utc"] = utc_now_iso()
        
        target_path = audit_report_path(job_id)
        with open(target_path, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2)
        
        # Log: AUDIT_REPORT_WRITTEN
        logger.log(
            event="AUDIT_REPORT_WRITTEN",
            job_id=job_id,
            zone="proofed",
            artifact_path=target_path,
            meta={"decision": report_data.get("decision")}
        )
        
        # Cleanup
        if processing_path.exists():
            processing_path.unlink()
        
        print(f"[auditor] SUCCESS: Generated report for {job_id} [{report_data['decision']}]")
        return True

    except Exception as e:
        error_msg = str(e)
        print(f"[auditor] ERR: Error in process_one_audit: {error_msg}")
        
        # Log: AUDIT_ERROR
        logger.log(
            event="AUDIT_ERROR",
            job_id=job_id if 'job_id' in locals() else "unknown",
            zone="proofed",
            meta={"error": error_msg}
        )
        
        # Update retry metadata
        update_retry_metadata(processing_path, error_msg)
        
        # Check if we should retry or move to dead letter
        try:
            metadata = json.loads(processing_path.read_text(encoding="utf-8"))
            if metadata.get("attempts", 0) >= MAX_ATTEMPTS:
                move_to_dead_letter(processing_path, f"Max retries after error: {error_msg}")
                circuit_breaker.record_failure()
            else:
                # Rename back to .json for retry
                processing_path.rename(processing_path.with_suffix(".json"))
                circuit_breaker.record_failure()
        except:
            # If we can't even read metadata, move to error
            try:
                processing_path.rename(processing_path.with_suffix(".error"))
            except:
                pass

async def auditor_relay_loop():
    print("[auditor] Background relay started, watching for audit requests...")
    iteration = 0
    
    while True:
        try:
            iteration += 1
            
            # Every 10 iterations (~10 minutes), reclaim stale processing
            if iteration % 10 == 0:
                reclaim_stale_processing()
            
            # Check for replay requests
            check_replay_requests()
            
            # Look for audit requests
            requests = list(PROOFED_DIR.glob("audit_request_*.json"))
            
            # Check circuit breaker before processing
            if not circuit_breaker.should_attempt():
                print("[auditor] [WARN] Circuit breaker OPEN, skipping audit processing")
            elif requests:
                # Process with Semaphore concurrency
                sem = asyncio.Semaphore(MAX_CONCURRENT_AUDITS)
                
                async def tasked_audit(req_path):
                    async with sem:
                        success = await process_one_audit(req_path)
                        if success:
                            circuit_breaker.record_success()
                        else:
                            circuit_breaker.record_failure()

                tasks = [tasked_audit(r) for r in requests[:20]] # Cap at 20 per cycle
                await asyncio.gather(*tasks)
                    
        except Exception as e:
            # Avoid emoji crash on Windows by using ascii(e)
            print(f"[auditor] Loop error: {ascii(e)}")
            circuit_breaker.record_failure()
        
        # Heartbeat to show it's alive (every 30s)
        pending_files = list(PROOFED_DIR.glob("audit_request_*.json"))
        processing_files = list(PROOFED_DIR.glob("*.processing"))
        failed_files = list(FAILED_DIR.glob("*.json"))
        
        print(f"[auditor] Heartbeat | Pending: {len(pending_files)} | Active: {len(processing_files)} | Failed: {len(failed_files)}")

        # Wait 30s before next check for better responsiveness while staying respectful of API
        await asyncio.sleep(30)

async def start_auditor_relay():
    """Start the auditor relay background task."""
    asyncio.create_task(auditor_relay_loop())
    print("[auditor] Relay task created")

if __name__ == "__main__":
    print("=" * 60)
    print("SHERATAN AUDITOR - LLM2 Relay")
    print("=" * 60)
    asyncio.run(auditor_relay_loop())
