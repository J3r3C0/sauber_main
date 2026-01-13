import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
import jsonschema

from core import config

class DecisionTraceLogger:
    def __init__(self, schema_path: str, log_path: str = "logs/decision_trace.jsonl"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(schema_path, "r", encoding="utf-8") as f:
            self.schema = json.load(f)
            
    def _now_iso(self) -> str:
        return datetime.utcnow().isoformat() + "Z"

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
        
        # Validation
        try:
            jsonschema.validate(instance=entry, schema=self.schema)
        except jsonschema.ValidationError as e:
            # We log it anyway but maybe add a warning to stderr
            print(f"[trace] Schema validation error: {e.message}", file=sys.stderr)
            # In production we might want to be stricter, but for now let's persist
            
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry) + "\n")
            
        return node_id

# Instantiate global logger
import sys
SCHEMA_FILE = Path(config.BASE_DIR) / "schemas" / "decision_trace_v1.json"
trace_logger = DecisionTraceLogger(str(SCHEMA_FILE))
