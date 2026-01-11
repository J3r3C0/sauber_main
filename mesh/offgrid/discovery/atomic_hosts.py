#!/usr/bin/env python3
import json, os, time
from pathlib import Path
from typing import Dict

HOSTS = Path("./discovery/mesh_hosts.json")

def _atomic_write(path: Path, text: str):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)

def merge_entry(endpoint: str, node_id: str, via: str, last_seen: int = None):
    HOSTS.parent.mkdir(parents=True, exist_ok=True)
    try:
        current = json.loads(HOSTS.read_text(encoding="utf-8"))
    except Exception:
        current = {}
    rec = current.get(endpoint, {})
    rec["node_id"] = node_id or rec.get("node_id", "?")
    rec["via"] = via or rec.get("via", "unknown")
    rec["last_seen"] = int(last_seen or time.time())
    current[endpoint] = rec
    _atomic_write(HOSTS, json.dumps(current, indent=2))
