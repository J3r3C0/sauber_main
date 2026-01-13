import json
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime

class ReplayEngine:
    def __init__(self, trace_logger):
        self.trace_logger = trace_logger

    def get_hash(self, data: Any) -> str:
        s = json.dumps(data, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(s.encode('utf-8')).hexdigest()

    def compare_determinism(self, original_result: Dict[str, Any], replay_result: Dict[str, Any]) -> str:
        orig_hash = self.get_hash(original_result.get("data") or original_result)
        repl_hash = self.get_hash(replay_result.get("data") or replay_result)
        
        if orig_hash == repl_hash:
            return "none"
        
        # Check for minor drift (e.g. only timestamp difference)
        # This is simplified: if keys match and most values match, it's minor
        return "major"

    def run_replay(self, node_id: str, mode: str = "exact") -> Dict[str, Any]:
        """
        In a real scenario, this would trigger the actual execution logic again.
        For now, it's a stub that simulates the decision flow.
        """
        # 1. Load original node from trace logs
        original = self._load_node(node_id)
        if not original:
            return {"ok": False, "error": "Node not found"}

        # 2. Extract inputs
        state = original["state"]
        action = original["action"]
        
        # 3. Simulate execution based on mode
        # mode: exact | counterfactual | regression
        
        return {
            "mode": mode,
            "original_node_id": node_id,
            "drift": "none", # Will be computed in real impl
            "ok": True
        }

    def _load_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        log_path = Path(self.trace_logger.log_path)
        if not log_path.exists(): return None
        
        with open(log_path, "r", encoding="utf-8") as f:
            for line in f:
                t = json.loads(line)
                if t["node_id"] == node_id:
                    return t
        return None

# Placeholder for replay runner integration
# In main core, we would hook this to rerun Dispatcher steps with captured state
