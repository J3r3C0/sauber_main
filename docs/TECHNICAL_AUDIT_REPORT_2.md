# Technical Audit Report #2 - Performance & Architecture Analysis

**Date:** 2026-01-13  
**Source:** External Performance & Architecture Review  
**Focus:** Bottlenecks, Test Results, Scalability

---

## Executive Summary

**System Quality:** ✅ Modular, stable in small-scale scenarios  
**Test Results:** ✅ Robust data integrity, no corruption detected  
**Primary Concern:** 🔴 File-based architecture limits scalability

**Key Finding:** System works well at current scale but will hit bottlenecks under higher load due to synchronous, file-based design.

---

## Test Results

### ✅ Tests Executed Successfully

#### 1. Atomic I/O Stress Test (`tests/test_atomic_save_stress.py`)
- **Setup:** 4 parallel processes, 100 writes each to same JSON file
- **Result:** ✅ **No data corruption detected**
- **Conclusion:** File locking and atomic writes are robust

#### 2. Lost Update Test (`tests/test_locking_lost_updates.py`)
- **Without Lock:** Only 63/200 increments persisted
- **With Lock:** ✅ **Exactly 200/200 increments persisted**
- **Conclusion:** `core/utils/atomic_io.py` lock mechanism works correctly

#### 3. Ledger Throughput Test (`tests/test_throughput.py`)
- **Single Transactions:** ~152 tx/s
- **Batched (10x):** ~278 tx/s
- **Improvement:** ✅ **1.8x speedup with batching**
- **Conclusion:** Batching significantly improves performance

#### 4. Multi-Node Sync Test (`tests/test_multinode_sync.py`)
- **Setup:** Ledger writer + replica sync, 10 credits
- **Result:** ✅ **Worker balance matched exactly**
- **Conclusion:** Replication and journal system works correctly

---

## Identified Bottlenecks

### 🔴 BOTTLENECK 1: Polling Loops

**Issue:**
- Worker loop: `time.sleep(1.0)` between checks
- Chain runner: Similar polling pattern
- Causes latency and limits throughput

**Current Code:**
```python
# worker/worker_loop.py
while running:
    process_jobs()
    time.sleep(1.0)  # ← Polling delay
```

**Impact:**
- Minimum 1-second latency per job
- Unnecessary filesystem scans
- Cannot scale to real-time processing

**Fix:**
```python
# Event-driven approach
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class JobHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.src_path.endswith('.job.json'):
            process_job(event.src_path)

observer = Observer()
observer.schedule(JobHandler(), 'data/webrelay_out')
observer.start()
```

**Priority:** 🔴 HIGH  
**Effort:** 4-6 hours  
**Impact:** Near-realtime job processing

---

### 🔴 BOTTLENECK 2: File-Based Queues

**Issue:**
- Inbox/Queue/Outbox managed via filesystem
- Directory scans become expensive with many files
- No native support for priorities, dependencies, idempotency

**Current Structure:**
```
mesh/runtime/
├── inbox/     # Input jobs
├── queue/     # Processing
└── outbox/    # Results
```

**Impact:**
- O(n) directory scans
- No atomic multi-file operations
- Difficult to implement priorities

**Fix:**
```python
# Use SQLite for queue management
import sqlite3

conn = sqlite3.connect('queue.db')
conn.execute('''
    CREATE TABLE jobs (
        id TEXT PRIMARY KEY,
        priority INTEGER,
        status TEXT,
        payload JSON,
        created_at TIMESTAMP
    )
''')
```

**Priority:** 🔴 HIGH  
**Effort:** 8-12 hours  
**Impact:** Scalable queue management

---

### 🟡 BOTTLENECK 3: Synchronous HTTP in Worker

**Issue:**
- Worker uses `requests.post()` synchronously
- Blocks entire loop on network issues
- No retry or timeout handling

**Current Code:**
```python
# worker/worker_loop.py
response = requests.post(
    f"{CORE_URL}/api/jobs/{job_id}/sync",
    json=result
)  # ← Blocks on network issues
```

**Impact:**
- Worker hangs on network problems
- No parallel job processing
- Single point of failure

**Fix:**
```python
# Async HTTP with retry
import httpx
import asyncio

async def report_result(job_id, result):
    async with httpx.AsyncClient() as client:
        for attempt in range(3):
            try:
                await client.post(
                    f"{CORE_URL}/api/jobs/{job_id}/sync",
                    json=result,
                    timeout=5.0
                )
                break
            except httpx.TimeoutException:
                await asyncio.sleep(2 ** attempt)
```

**Priority:** 🟡 MEDIUM  
**Effort:** 3-4 hours  
**Impact:** Resilient worker loop

---

### 🟡 BOTTLENECK 4: Global File Locking

**Issue:**
- `json_lock` creates `.lock` file per JSON
- Works per-file but prevents parallel operations
- Lock contention with many concurrent processes

**Current Implementation:**
```python
# core/utils/atomic_io.py
with json_lock(filepath):
    # Entire file locked
    save_json(filepath, data)
```

**Impact:**
- No parallel operations on different accounts
- Lock contention under load
- Serializes all writes

**Fix:**
```python
# Fine-grained locking or use SQLite transactions
# SQLite handles concurrent access natively
conn.execute('BEGIN IMMEDIATE')
conn.execute('UPDATE accounts SET balance = ? WHERE id = ?', ...)
conn.commit()
```

**Priority:** 🟡 MEDIUM  
**Effort:** 6-8 hours (migration to SQLite)  
**Impact:** Higher parallelism

---

### 🟡 BOTTLENECK 5: Cumulative JSON Snapshots

**Issue:**
- Ledger saves entire state on every transaction
- File size grows with number of accounts
- I/O overhead increases linearly

**Current Code:**
```python
# mesh/registry/ledger_service.py
def credit(self, worker_id, amount):
    # ... update in-memory state ...
    self.save_state()  # ← Writes entire state
```

**Impact:**
- Growing I/O cost
- Wasted bandwidth
- Slow with many accounts

**Fix:**
```python
# Delta events + periodic snapshots
def credit(self, worker_id, amount):
    event = {"type": "credit", "worker": worker_id, "amount": amount}
    append_event(event)  # ← Only delta
    
    if event_count % 1000 == 0:
        save_snapshot()  # ← Periodic full snapshot
```

**Priority:** 🟡 MEDIUM  
**Effort:** 4-6 hours  
**Impact:** Constant-time writes

---

### 🟢 BOTTLENECK 6: State Machine Logging Overhead

**Issue:**
- `_append_event()` opens log file on every transition
- Synchronous writes
- High I/O overhead with frequent state changes

**Current Code:**
```python
# core/state_machine.py
def _append_event(self, ev):
    with open(self.log_path, "a") as f:  # ← Opens file each time
        f.write(ev.to_json() + "\n")
```

**Impact:**
- File open/close overhead
- No buffering
- Slow with frequent transitions

**Fix:**
```python
# Use rotating log handler
import logging
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    'state_transitions.jsonl',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
logger = logging.getLogger('state_machine')
logger.addHandler(handler)

def _append_event(self, ev):
    logger.info(ev.to_json())  # ← Buffered writes
```

**Priority:** 🟢 LOW  
**Effort:** 1-2 hours  
**Impact:** Reduced I/O overhead

---

### 🟢 BOTTLENECK 7: Sequential Health Probes

**Issue:**
- `mesh/registry/health_prober.py` pings hosts sequentially
- Detection time increases with number of hosts
- No async framework

**Impact:**
- Slow health checks with many hosts
- Delayed failure detection

**Fix:**
```python
# Async parallel health checks
import asyncio
import aiohttp

async def check_all_hosts(hosts):
    async with aiohttp.ClientSession() as session:
        tasks = [check_host(session, host) for host in hosts]
        return await asyncio.gather(*tasks)
```

**Priority:** 🟢 LOW  
**Effort:** 2-3 hours  
**Impact:** Faster health monitoring

---

## Recommended Next Steps (Priority Order)

### Phase 1: Critical Performance Fixes (Week 1)

| # | Task | Effort | Impact |
|---|------|--------|--------|
| 1 | **Event-driven worker** (replace polling) | 4-6h | Near-realtime processing |
| 2 | **Async HTTP in worker** | 3-4h | Resilient job reporting |
| 3 | **State machine file locking** (from Audit #1) | 1-2h | Data integrity |

### Phase 2: Scalability Improvements (Week 2-3)

| # | Task | Effort | Impact |
|---|------|--------|--------|
| 4 | **SQLite queue backend** | 8-12h | Scalable queue management |
| 5 | **Ledger delta events** | 4-6h | Constant-time writes |
| 6 | **Fine-grained locking** (or SQLite migration) | 6-8h | Higher parallelism |

### Phase 3: Production Features (Week 4+)

| # | Task | Effort | Impact |
|---|------|--------|--------|
| 7 | **Async health probes** | 2-3h | Faster monitoring |
| 8 | **Rotating log handlers** | 1-2h | Reduced I/O |
| 9 | **Production features** (from refactoring plan) | 20-30h | Enterprise-ready |

---

## Production Features (From Refactoring Plan)

**Mentioned in README but not yet implemented:**

- ✅ Idempotency
- ✅ Retry logic
- ✅ Timeouts
- ✅ Priority queues
- ✅ SQLite storage
- ✅ Host health checks
- ✅ Rate limiting

**Recommendation:** Prioritize these after Phase 1-2 fixes.

---

## Architecture Recommendations

### Current: File-Based, Synchronous
```
Worker (sync) → Files → Core (sync) → Files → Mesh
```

**Pros:**
- Simple
- Easy to debug
- Works at small scale

**Cons:**
- Polling latency
- File I/O overhead
- Limited parallelism

### Recommended: Event-Driven, Async
```
Worker (async) → SQLite Queue → Core (async) → Message Bus → Mesh
```

**Pros:**
- Near-realtime
- Scalable
- Higher throughput

**Cons:**
- More complex
- Requires migration

**Migration Path:**
1. Keep file-based as fallback
2. Implement SQLite queue in parallel
3. Gradually migrate components
4. Remove file-based once stable

---

## Configuration & Dependencies

### Issue: Missing Dependencies Block Tests

**Problem:**
- Tests failed due to missing `python-dotenv`
- Optional dependencies should not block core functionality

**Fix:**
```python
# Use fallbacks
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # Use defaults

# Or provide in-code defaults
CORE_PORT = int(os.getenv('CORE_PORT', 8001))
```

**Recommendation:**
- Create `pyproject.toml` or root `requirements.txt`
- Document optional vs required dependencies
- Provide sensible defaults

---

## Overall Assessment

| Aspect | Rating | Notes |
|--------|--------|-------|
| **Data Integrity** | ✅ Excellent | No corruption in stress tests |
| **Small-Scale Performance** | ✅ Good | Works well at current load |
| **Scalability** | 🟡 Limited | File-based design limits growth |
| **Architecture** | 🟡 Solid but synchronous | Needs async refactor |
| **Test Coverage** | ✅ Good | Core functionality well-tested |

---

## Conclusion

Sheratan is **stable and well-designed** for current scale. The modular architecture and clear boundaries (mesh-internal vs mesh-external) are excellent. However, the **file-based, synchronous design will become a bottleneck** under higher load.

**Recommended Focus:**
1. **Immediate:** Event-driven worker + async HTTP (Phase 1)
2. **Short-term:** SQLite queue + delta events (Phase 2)
3. **Long-term:** Full async architecture + production features (Phase 3)

This maintains the philosophy of **Nachvollziehbarkeit** (traceability) while improving performance and scalability.

---

**Document Version:** 1.0  
**Next Review:** After Phase 1 implementation  
**Related:** [TECHNICAL_AUDIT_REPORT_1.md](TECHNICAL_AUDIT_REPORT_1.md)
