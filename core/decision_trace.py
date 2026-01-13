import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import jsonschema

from core import config

class DecisionTraceLogger:
    """
    Hard schema-validating logger for MCTS decision traces.
    
    Rules:
    - Valid events → logs/decision_trace.jsonl
    - Invalid events → logs/decision_trace_breaches.jsonl (separate)
    - No invalid events ever pollute the main stream
    """
    
    def __init__(self, schema_path: str, log_path: str = "logs/decision_trace.jsonl"):
        self.log_path = Path(log_path)
        self.breach_path = self.log_path.parent / "decision_trace_breaches.jsonl"
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(schema_path, "r", encoding="utf-8") as f:
            self.schema = json.load(f)
            
    def _now_iso(self) -> str:
        return datetime.utcnow().isoformat() + "Z"
    
    def _log_breach(self, entry: Dict[str, Any], validation_error: 'jsonschema.ValidationError'):
        """
        Log schema validation breach to separate file with structured error info.
        
        Breach format:
        - timestamp
        - schema_version
        - error: {message, validator, path}
        - raw_event_truncated (max 4000 chars)
        """
        # Extract structured error info
        error_info = {
            "message": str(validation_error.message),
            "validator": validation_error.validator,
            "path": "/" + "/".join(str(p) for p in validation_error.absolute_path) if validation_error.absolute_path else "/"
        }
        
        # Truncate raw event to 4000 chars
        raw_str = json.dumps(entry)
        raw_truncated = raw_str[:4000] + "..." if len(raw_str) > 4000 else raw_str
        
        breach_entry = {
            "timestamp": self._now_iso(),
            "schema_version": "decision_trace_v1",
            "error": error_info,
            "raw_event_truncated": raw_truncated
        }
        
        with open(self.breach_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(breach_entry) + "\n")
        
        print(f"[BREACH] Schema validation failed: {error_info['message']} at {error_info['path']}", file=sys.stderr)

    def log_node(
        self,
        trace_id: str,
        intent: str,
        build_id: str,
        state: Dict[str, Any],
        action: Dict[str, Any],
        result: Dict[str, Any],
        job_id: Optional[str] = None,
        parent_node_id: Optional[str] = None,
        depth: int = 0
    ) -> str:
        """
        Log a decision node. Returns node_id on success, raises on validation failure.
        
        Valid events are written to main log.
        Invalid events are written to breach log and raise ValueError.
        """
        node_id = str(uuid.uuid4())
        
        entry = {
            "schema_version": "decision_trace_v1",
            "timestamp": self._now_iso(),
            "trace_id": trace_id,
            "node_id": node_id,
            "parent_node_id": parent_node_id,
            "build_id": build_id,
            "job_id": job_id,
            "intent": intent,
            "depth": depth,
            "state": state,
            "action": action,
            "result": result
        }
        
        # Hard validation
        try:
            jsonschema.validate(instance=entry, schema=self.schema)
        except jsonschema.ValidationError as e:
            # Log to breach file with structured error
            self._log_breach(entry, e)
            # Do NOT write to main log
            raise ValueError(f"Schema breach: {e.message}")
        
        # Only valid events reach here
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
            
        return node_id

# Instantiate global logger
import sys
SCHEMA_FILE = Path(config.BASE_DIR) / "schemas" / "decision_trace_v1.json"
trace_logger = DecisionTraceLogger(str(SCHEMA_FILE))
