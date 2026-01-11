# core/chain_index.py
"""
Chain Index - Maps job_id to chain metadata
Zero-intrusion approach: metadata stored separately from Job model
"""

import json
import os
import tempfile
from typing import Any, Dict, Optional


class ChainIndex:
    """Atomic index mapping job_id -> chain routing info."""
    
    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        if not os.path.exists(self.path):
            self._atomic_write({"jobs": {}})
    
    def _read(self) -> Dict[str, Any]:
        """Read index file."""
        with open(self.path, "r", encoding="utf-8") as f:
            return json.load(f)
    
    def _atomic_write(self, data: Dict[str, Any]) -> None:
        """Atomic write using temp file + replace."""
        d = os.path.dirname(self.path)
        fd, tmp = tempfile.mkstemp(prefix="chain_index_", suffix=".json", dir=d)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            os.replace(tmp, self.path)
        finally:
            try:
                if os.path.exists(tmp):
                    os.remove(tmp)
            except Exception:
                pass
    
    def put(self, job_id: str, info: Dict[str, Any]) -> None:
        """Store chain info for job_id."""
        data = self._read()
        data.setdefault("jobs", {})[job_id] = info
        self._atomic_write(data)
    
    def get(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Get chain info for job_id."""
        data = self._read()
        return data.get("jobs", {}).get(job_id)
    
    def delete(self, job_id: str) -> None:
        """Remove chain info for job_id."""
        data = self._read()
        if job_id in data.get("jobs", {}):
            del data["jobs"][job_id]
            self._atomic_write(data)
