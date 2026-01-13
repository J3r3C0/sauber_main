# Technical Audit Report #1 - System Risks & Recommendations

**Date:** 2026-01-13  
**Source:** External Technical Review  
**Status:** Action Items Identified

---

## Executive Summary

**System Quality:** ✅ Serious, production-grade system
- Clear module boundaries
- Minimal technical debt
- Phase A (State Machine) well integrated
- Clean repository structure

**Primary Risk:** 🔴 Concurrency/Locking issues in state persistence

---

## Critical Risks & Fixes

### 🔴 RISK 1: State Machine Persistence Without Locks

**Issue:**
- `core/state_machine.py` persists snapshots via `tmp + os.replace` (good)
- **NO file locking** implemented
- Multiple processes can write simultaneously:
  - Core lifespan (startup/shutdown)
  - Background loops
  - Tests/tools

**Consequence:**
- Race conditions → state flaps
- Corrupted JSONL order
- Data loss in concurrent scenarios

**Fix (High Priority):**
```python
# Add file locking for snapshot + JSONL append
# Use: portalocker / fasteners / custom lockfile

import portalocker

def _persist_snapshot(self, snap):
    with portalocker.Lock(self.load_path + ".lock", timeout=5):
        # existing persist logic
        ...

def _append_event(self, ev):
    with portalocker.Lock(self.log_path + ".lock", timeout=5):
        # existing append logic
        ...
```

**Priority:** 🔴 CRITICAL  
**Effort:** 1-2 hours  
**Impact:** Prevents data corruption in production

---

### 🟡 RISK 2: Health Evaluation - Critical vs Non-Critical Not Utilized

**Issue:**
- Health check has `critical=True/False` flags
- Current logic: **any service down → DEGRADED**
- Doesn't differentiate between critical and non-critical failures

**Current Code:**
```python
if critical_down:
    overall = "degraded"  # Critical service down
elif non_critical_down:
    overall = "degraded"  # Non-critical services down
```

**Consequence:**
- Dashboard can't distinguish severity
- No granular degradation states
- Alerts treat all failures equally

**Fix (Medium Priority):**
```python
if critical_down:
    overall = "degraded_critical"
    meta["severity"] = "critical"
    meta["affected_services"] = critical_down
elif non_critical_down:
    overall = "degraded_minor"
    meta["severity"] = "minor"
    meta["affected_services"] = non_critical_down
else:
    overall = "operational"
```

**Priority:** 🟡 MEDIUM  
**Effort:** 2-3 hours  
**Impact:** Better observability and alerting

---

### 🟡 RISK 3: Hardcoded Ports in Health Check

**Issue:**
- Ports hardcoded in `_evaluate_system_health()`:
  ```python
  {"name": "Core API", "port": 8001, "critical": True},
  {"name": "WebRelay", "port": 3000, "critical": True},
  ```
- Becomes maintenance bottleneck when:
  - Ports change
  - Docker/WSL/Reverse-proxy added
  - Multi-node deployment

**Fix (Medium Priority):**
```python
# Load from config
from core.config import CORE_PORT, WEBRELAY_PORT, BROKER_PORT

services = [
    {"name": "Core API", "port": CORE_PORT, "critical": True},
    {"name": "WebRelay", "port": WEBRELAY_PORT, "critical": True},
    # ... from config
]
```

**Priority:** 🟡 MEDIUM  
**Effort:** 1 hour  
**Impact:** Easier configuration management

---

### 🟡 RISK 4: Dual "Source of Truth" - Core vs External

**Issue:**
- Multiple implementations of same concepts:
  - `core/webrelay_*` (Bridge/Clients)
  - `external/webrelay/*` (TS WebRelay Service)
  - `external/dashboard/*`
- Risk of drift: fix in core, forget external

**Fix (Strategic):**
- **Rule:** Core defines interfaces + schemas, external/ implements clients only
- Centralize schemas in `spec/` or `core/models.py`
- Export JSON schemas for external services
- Version API contracts

**Priority:** 🟢 LOW (Strategic)  
**Effort:** 4-6 hours  
**Impact:** Long-term maintainability

---

### 🟡 RISK 5: Sync HTTP Calls in FastAPI Context

**Issue:**
- `core/webrelay_llm_client.py` uses synchronous `requests`
- Safe in worker threads
- **Blocks event loop** if called in FastAPI request handlers

**Fix (Medium Priority):**
```python
# Option 1: Use async client
import httpx
async with httpx.AsyncClient() as client:
    response = await client.post(...)

# Option 2: Run in thread pool
from starlette.concurrency import run_in_threadpool
result = await run_in_threadpool(sync_http_call)
```

**Priority:** 🟡 MEDIUM  
**Effort:** 2-3 hours  
**Impact:** Prevents FastAPI blocking

---

## Recommended Next Steps

### Phase B: Deterministic Responsibility (RECOMMENDED)

**Why Now:**
- State Machine (Phase A) provides "system awareness"
- Phase B adds "action justification"
- Natural progression of audit philosophy

**What to Implement:**
For every decision (routing, retry, fallback, chain dispatch):
- `decision_id` - Unique identifier
- `input_context` - Small, hashed context
- `rule/model_used` - Which logic made the decision
- `reason` - Human-readable justification
- `output_action` - What was decided
- `result_ref` - Where the result is stored

**Deliverables:**
1. `core/decision_log.py` (append-only, locked)
2. Integration hooks in `job_chain_manager.py` + `chain_runner.py`
3. API endpoint: `/api/system/decisions` (read-only)

**Effort:** 6-8 hours  
**Impact:** Complete audit trail (Soll-Erfüllung → ~90%)

---

## Mini-Roadmap (Priority Order)

| # | Task | Priority | Effort | Impact |
|---|------|----------|--------|--------|
| 1 | **State persistence locks** | 🔴 CRITICAL | 1-2h | Prevents data corruption |
| 2 | **Health config from .env** | 🟡 MEDIUM | 1h | Easier deployment |
| 3 | **Critical vs non-critical health** | 🟡 MEDIUM | 2-3h | Better observability |
| 4 | **Phase B: Decision Journal** | 🟢 HIGH VALUE | 6-8h | Audit completeness |
| 5 | **Fail simulation tests** | 🟢 MEDIUM | 3-4h | Verify degradation |
| 6 | **Dashboard state/decision stream** | 🟢 LOW | 4-6h | Visualization |

---

## Overall Technical Assessment

| Aspect | Rating | Notes |
|--------|--------|-------|
| **Core Stability** | ✅ Strong | Clean architecture, minimal debt |
| **Phase A Integration** | ✅ Excellent | Well-designed, properly integrated |
| **Biggest Risk** | 🔴 Concurrency | State/log locking needed |
| **Best Next Step** | ✅ Phase B | Aligns with audit philosophy |

---

## Action Items for Next Session

### Immediate (Before Production)
- [ ] Add file locking to `state_machine.py`
- [ ] Add file locking to JSONL append

### Short-term (This Week)
- [ ] Move ports to config
- [ ] Implement critical vs non-critical health states
- [ ] Review async/sync HTTP usage

### Medium-term (Next Sprint)
- [ ] Implement Phase B (Decision Journal)
- [ ] Create fail simulation tests
- [ ] Dashboard integration for state/decisions

---

**Document Version:** 1.0  
**Next Review:** After implementing file locks  
**Awaiting:** Second audit report analysis
