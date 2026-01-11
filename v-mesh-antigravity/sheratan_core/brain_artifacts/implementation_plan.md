# Implementation Plan: Event-Based Storage with Persistent Outbox

## Problem Statement (Revised)
The Offgrid Memory infrastructure (compact.py, retention.py, synopses.py, etype system) **already exists**, but Sheratan Core doesn't utilize it properly:
1. All data is sent as generic `etype=2` instead of semantic event types
2. Compaction/Retention mechanisms are never invoked
3. Replication uses ephemeral threads (crash-unsafe)

## User Review Required

> [!IMPORTANT]
> This plan **leverages existing Offgrid components** instead of reinventing them. We integrate the Event-Type system with a persistent Outbox.

**Key Changes:**
- Define semantic event types for Missions/Tasks/Jobs
- Use existing `compact.py` for micro-summaries
- Add persistent Outbox for crash-safe replication

## Proposed Changes

### Component 1: Event Type Definitions

#### [NEW] [event_types.py](file:///c:/Projects/2_sheratan_core/core/sheratan_core_v2/event_types.py)

```python
"""
Event type definitions for Offgrid Memory integration.
Aligns with memory/store.py etype field.
"""

# Core Data Events (10-19)
ETYPE_MISSION_CREATED = 10
ETYPE_MISSION_UPDATED = 11
ETYPE_TASK_CREATED = 12
ETYPE_TASK_UPDATED = 13
ETYPE_JOB_CREATED = 14
ETYPE_JOB_UPDATED = 15

# Job Lifecycle Events (20-29)
ETYPE_JOB_DISPATCHED = 20
ETYPE_JOB_RESULT = 21
ETYPE_JOB_FAILED = 22

# Ledger Events (30-39)
ETYPE_LEDGER_TX = 30

def get_etype_for_operation(entity_type: str, operation: str) -> int:
    """Map entity/operation to etype."""
    mapping = {
        ("mission", "create"): ETYPE_MISSION_CREATED,
        ("mission", "update"): ETYPE_MISSION_UPDATED,
        ("task", "create"): ETYPE_TASK_CREATED,
        ("task", "update"): ETYPE_TASK_UPDATED,
        ("job", "create"): ETYPE_JOB_CREATED,
        ("job", "update"): ETYPE_JOB_UPDATED,
    }
    return mapping.get((entity_type, operation), 2)  # Default: generic E2EE
```

---

### Component 2: Persistent Outbox

#### [NEW] [outbox.py](file:///c:/Projects/2_sheratan_core/core/sheratan_core_v2/outbox.py)

```python
import sqlite3
import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any

class ReplicationOutbox:
    """SQLite-based persistent queue for Offgrid replication jobs."""
    
    def __init__(self, db_path: str = "./data/outbox.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30)
        self._init_db()
    
    def _init_db(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS outbox (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL,
                data_json TEXT NOT NULL,
                etype INTEGER NOT NULL,
                required_acks REAL NOT NULL,
                created_ts INTEGER NOT NULL,
                retry_count INTEGER DEFAULT 0,
                last_error TEXT,
                status TEXT DEFAULT 'pending'
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON outbox(status)")
        self.conn.commit()
    
    def enqueue(self, key: str, data: dict, etype: int, required_acks: float = 1.0):
        ts = int(time.time() * 1000)
        self.conn.execute(
            "INSERT INTO outbox (key, data_json, etype, required_acks, created_ts) VALUES (?, ?, ?, ?, ?)",
            (key, json.dumps(data), etype, required_acks, ts)
        )
        self.conn.commit()
    
    def get_pending(self, limit: int = 10) -> List[Dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT id, key, data_json, etype, required_acks, retry_count FROM outbox WHERE status='pending' LIMIT ?",
            (limit,)
        )
        return [
            {"id": r[0], "key": r[1], "data": json.loads(r[2]), "etype": r[3], "required_acks": r[4], "retry_count": r[5]}
            for r in cur.fetchall()
        ]
    
    def mark_success(self, job_id: int):
        self.conn.execute("UPDATE outbox SET status='completed' WHERE id=?", (job_id,))
        self.conn.commit()
    
    def mark_failed(self, job_id: int, error: str):
        self.conn.execute(
            "UPDATE outbox SET retry_count=retry_count+1, last_error=? WHERE id=?",
            (error, job_id)
        )
        self.conn.commit()
```

---

### Component 3: Enhanced Storage Adapter

#### [MODIFY] [storage_adapter.py](file:///c:/Projects/2_sheratan_core/core/sheratan_core_v2/storage_adapter.py)

**Changes:**
1. Import `event_types` and `outbox`
2. Pass `etype` to `store_with_quorum()`
3. Replace thread with outbox enqueue
4. Add background worker

```python
from .event_types import get_etype_for_operation
from .outbox import ReplicationOutbox
import threading
import time

class HybridStorage:
    def __init__(self, storage_mod, offgrid_client=None):
        # ... existing code ...
        self.outbox = ReplicationOutbox() if self.enabled else None
        
        if self.enabled:
            self._worker_thread = threading.Thread(target=self._process_outbox, daemon=True)
            self._worker_thread.start()
    
    def create_mission(self, mission):
        self._create_mission(mission)
        etype = get_etype_for_operation("mission", "create")
        self._replicate(f"mission:{mission.id}", mission.to_dict(), etype, required=1.0)
    
    def _replicate(self, key: str, data: dict, etype: int, required: float = 1.0):
        if not self.enabled:
            return
        self.outbox.enqueue(key, data, etype, required)
    
    def _process_outbox(self):
        while True:
            try:
                jobs = self.outbox.get_pending(limit=5)
                for job in jobs:
                    try:
                        # Pass etype to offgrid_memory client
                        eid = self.offgrid.store_with_quorum(
                            job["key"], job["data"], job["etype"], job["required_acks"]
                        )
                        if eid:
                            self.outbox.mark_success(job["id"])
                    except Exception as e:
                        self.outbox.mark_failed(job["id"], str(e))
                time.sleep(2)
            except Exception as e:
                print(f"[outbox] Worker error: {e}")
                time.sleep(5)
```

---

### Component 4: Enhanced Offgrid Memory Client

#### [MODIFY] [offgrid_memory.py](file:///c:/Projects/2_sheratan_core/core/sheratan_core_v2/offgrid_memory.py)

**Changes:**
Add `etype` parameter to `store_with_quorum()`:

```python
def store_with_quorum(self, key: str, data: dict, etype: int = 2, required_acks: float = 1.0):
    data_bytes = json.dumps(data).encode('utf-8')
    meta = {
        "key": key, 
        "type": "core_archive", 
        "encrypted": True, 
        "owner": self.identity.node_id,
        "etype": etype  # ← NEW
    }
    
    # ... existing encryption logic ...
    
    resp = self.session.post(
        f"{host_url}/memory/ingest",
        data=payload_bytes,
        headers={
            "X-Meta": json.dumps(meta),
            "X-Score": "1.0",
            "X-Type": str(etype)  # ← Use semantic etype
        },
        timeout=5
    )
```

---

### Component 5: Compaction Daemon (Optional)

#### [NEW] [compaction_daemon.py](file:///c:/Projects/2_sheratan_core/core/sheratan_core_v2/compaction_daemon.py)

```python
"""
Background daemon that periodically compacts Offgrid Memory events.
Uses existing compact.py from Offgrid.
"""
import time
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '../../offgrid-net-v0.16.4-with-memory-PRO-UI-POLICY-ROTATE'))

from memory.store import MemoryStore
from memory.compact import compact_window

def run_compaction_daemon(interval_seconds: int = 1800):
    """Run compaction every 30 minutes."""
    store = MemoryStore()
    
    while True:
        try:
            # Get events from last window
            cutoff = int(time.time() * 1000) - (interval_seconds * 1000)
            events = store.query_events(since_ts=cutoff, limit=1000)
            
            if events:
                window_id = f"window_{int(time.time())}"
                result = compact_window(events, window_id, reservoir_k=32)
                print(f"[compaction] Created summary {window_id}: {result}")
        except Exception as e:
            print(f"[compaction] Error: {e}")
        
        time.sleep(interval_seconds)
```

---

## Verification Plan

### Test 1: Event Type Verification
```powershell
# Create mission → Check etype in memory/store
Invoke-WebRequest -Uri "http://localhost:8001/api/missions" -Method Post -Body '{"title":"Test","description":"X"}'
Invoke-WebRequest -Uri "http://localhost:8081/memory/query?limit=1" | ConvertFrom-Json | Select -ExpandProperty events | Select etype
# Expected: etype = 10 (MISSION_CREATED)
```

### Test 2: Outbox Persistence
```powershell
# Create mission → Kill Core → Restart → Verify replication completes
```

### Test 3: Compaction
```powershell
# Run compaction daemon → Check summary files in OFFGRID_SUMMARY_DIR
```

---

## Migration Notes

**Backward Compatibility:** Existing data (etype=2) remains valid. New operations use semantic types.

**Rollout:**
1. Implement event_types.py + outbox.py
2. Update storage_adapter.py
3. Update offgrid_memory.py
4. (Optional) Add compaction daemon
