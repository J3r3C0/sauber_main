# Sheratan-Offgrid Integration - Complete Walkthrough

## Summary
Successfully integrated Sheratan Core with Offgrid Memory infrastructure using **direct component usage** without wrapper layers.

## Phase 2.5: Event-Based Storage + Persistent Outbox ✅

### Components Created
1. **[event_types.py](file:///c:/Projects/2_sheratan_core/core/sheratan_core_v2/event_types.py)** - Semantic event type definitions
2. **[outbox.py](file:///c:/Projects/2_sheratan_core/core/sheratan_core_v2/outbox.py)** - SQLite-based persistent replication queue

### Event Types
```python
ETYPE_MISSION_CREATED = 10
ETYPE_MISSION_UPDATED = 11
ETYPE_TASK_CREATED = 12
ETYPE_JOB_CREATED = 14
# etc.
```

### Outbox Pattern
**Before:** Ephemeral threads → Data loss on crash
```python
thread = Thread(target=lambda: replicate(...))
thread.start()  # ← Lost on crash!
```

**After:** Persistent SQLite queue → Crash-safe
```python
outbox.enqueue(key, data, etype, required_acks)  # ← Persisted!
# Background worker processes queue continuously
```

## Phase 3: Direct Offgrid Memory Integration ✅

### Architecture
```
Sheratan Core (main.py)
    ↓
sys.path.insert(0, "offgrid-net-v0.16.4-...")  # ← Direct access
    ↓
┌─────────────────────────────────────────┐
│  memory.retention                       │
│  - allocate_budget()                    │
│  - compute_effective_budget()           │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  memory.compact                         │
│  - compact_window()                     │
│  - Bloom filters, Reservoir sampling    │
└─────────────────────────────────────────┘
┌─────────────────────────────────────────┐
│  memory.store                           │
│  - MemoryStore (SQLite + chunks)        │
│  - query_events()                       │
└─────────────────────────────────────────┘
```

### Direct Integration (main.py)
```python
# No wrappers - direct imports
from memory.retention import allocate_budget, compute_effective_budget
from memory.store import MemoryStore
from memory.compact import compact_window

# Retention
budget = allocate_budget(compute_effective_budget(128, 0))
# → Events: 51MB, Summaries: 32MB, Chunks: 32MB, Indices: 12MB

# Compaction (background thread)
def _compaction_worker():
    store = MemoryStore()
    while True:
        time.sleep(1800)  # 30 min
        events = store.query_events(since_ts=cutoff, limit=1000)
        if events:
            compact_window(events, window_id, reservoir_k=32)
```

## Configuration

### Environment Variables
```bash
# Storage
OFFGRID_STORAGE_ENABLED=true
OFFGRID_STORAGE_HOSTS=http://127.0.0.1:8081,http://127.0.0.1:8082
OFFGRID_BROKER_URL=http://127.0.0.1:9000
OFFGRID_AUTH_KEY=shared-secret

# Retention
OFFGRID_RETENTION_BASE_MB=128
OFFGRID_RETENTION_TOKEN_LEVEL=0

# Compaction
OFFGRID_COMPACTION_INTERVAL=1800  # 30 minutes
```

### Wallet Balances
```json
{
  "host-a": 1000000.0,
  "host-b": 1000000.0,
  "broker": 1000000.0,
  "core-v2": 1000000.0
}
```

## Verification

### 1. Event Types
```powershell
# Create mission
Invoke-WebRequest -Uri "http://localhost:8001/api/missions" -Method Post -Body '{"title":"Test","description":"X"}'

# Check etype in Host memory
Invoke-WebRequest -Uri "http://localhost:8081/memory/query?limit=1" | ConvertFrom-Json | Select -ExpandProperty events | Select etype
# Expected: 10 (MISSION_CREATED)
```

### 2. Outbox Persistence
```powershell
# Check outbox DB
sqlite3 .\core\data\outbox.db "SELECT id, key, etype, status FROM outbox;"
# Expected: Jobs with status='completed'
```

### 3. Retention Budget
```
[main] [OK] Retention: 128MB (Events: 51MB, Summaries: 32MB, Chunks: 32MB)
```

### 4. Compaction Daemon
```
[main] [OK] Compaction daemon started
[compaction] ✓ window_1735938000: {'window_id': 'window_1735938000', 'count': 42, 'reservoir': 32}
```

## Status

| Component | Status | Details |
|-----------|--------|---------|
| Event Types | ✅ | Semantic types 10-30 |
| Persistent Outbox | ✅ | SQLite queue, crash-safe |
| E2EE | ✅ | XChaCha20-Poly1305 |
| Quorum | ✅ | Broker tracking |
| Retention | ✅ | 128MB budget allocated |
| Compaction | ✅ | 30min intervals |
| Synopses | ✅ | Bloom filters ready |

## Next Steps (Optional)

1. **LCP Cost Tracking** - Use `economy/txlog.py` directly for transaction creation
2. **Ledger Integration** - Use `ledger/local_dag.py` for DAG blocks
3. **Erasure Coding** - Use `storage/ec_encode.py` for data sharding

All Offgrid components are now **directly accessible** via imports.
