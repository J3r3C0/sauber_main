# Phase 2 Decision Matrix

**Date:** 2026-01-13  
**Purpose:** Determine when and which Phase 2 upgrades are worth implementing

---

## Executive Summary

Phase 2 is **not mandatory** - it's a **scalability upgrade**.  
Your system is **stable now**, not "finished".

This matrix helps you decide:
- **When** to implement each Phase 2 feature
- **Which** features to prioritize
- **Whether** to implement at all

---

## Decision Framework

### Three Questions Per Feature

1. **Do we have the problem this solves?**
2. **Is the ROI worth the complexity?**
3. **Can we defer it without risk?**

If answers are: No / No / Yes → **Don't implement**

---

## Phase 2 Features Overview

| Feature | Complexity | Impact | When Needed |
|---------|------------|--------|-------------|
| **SQLite Queue** | HIGH | HIGH | Many jobs, multiple workers |
| **Ledger Delta Events** | MEDIUM | MEDIUM | Many accounts, high tx rate |
| **Async Health Probes** | LOW | LOW | Many hosts (>10) |
| **Fine-Grained Locking** | HIGH | MEDIUM | High concurrency |
| **Rotating Log Handlers** | LOW | LOW | Large log files |

---

## Feature 1: SQLite Queue Backend

### Current: File-Based Queue
```
data/webrelay_out/*.job.json  (inbox)
data/webrelay_in/*.result.json (outbox)
```

### Proposed: SQLite Queue
```sql
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    priority INTEGER,
    status TEXT,
    payload JSON,
    created_at TIMESTAMP
)
```

### When to Implement

**Implement if:**
- ✅ Processing > 100 jobs/hour consistently
- ✅ Running multiple worker instances
- ✅ Need job priorities
- ✅ Need job dependencies
- ✅ Directory scans become slow (>1000 files)

**Don't implement if:**
- ❌ < 50 jobs/hour
- ❌ Single worker instance
- ❌ No priority requirements
- ❌ File-based works fine

### Metrics to Watch

```powershell
# Job count in queue
(Get-ChildItem data\webrelay_out\*.job.json).Count

# Directory scan time
Measure-Command { Get-ChildItem data\webrelay_out\*.job.json }
```

**Threshold:** If scan time > 100ms or queue > 1000 files → Consider SQLite

### Complexity Assessment

| Aspect | Rating | Notes |
|--------|--------|-------|
| **Implementation** | 🔴 HIGH | Full queue rewrite |
| **Migration** | 🟡 MEDIUM | Need migration script |
| **Testing** | 🔴 HIGH | Concurrency tests critical |
| **Rollback** | 🟡 MEDIUM | Can revert to files |

### ROI Calculation

**Benefits:**
- Atomic operations (no `.claimed` files)
- Native priorities
- Faster queries
- Better concurrency

**Costs:**
- 8-12 hours implementation
- Migration complexity
- New failure modes (DB corruption)

**Verdict:** Implement only if **scaling beyond single worker**

---

## Feature 2: Ledger Delta Events

### Current: Full Snapshot on Every Write
```python
def credit(worker_id, amount):
    # Update in-memory state
    self.balances[worker_id] += amount
    # Save ENTIRE state
    self.save_state()  # Writes all accounts
```

### Proposed: Delta Events + Snapshots
```python
def credit(worker_id, amount):
    # Append delta event
    append_event({"type": "credit", "worker": worker_id, "amount": amount})
    
    # Snapshot every 1000 events
    if event_count % 1000 == 0:
        save_snapshot()
```

### When to Implement

**Implement if:**
- ✅ > 100 accounts in ledger
- ✅ > 1000 transactions/day
- ✅ Ledger save time > 100ms
- ✅ Ledger file size > 1MB

**Don't implement if:**
- ❌ < 50 accounts
- ❌ < 100 transactions/day
- ❌ Save time < 50ms

### Metrics to Watch

```powershell
# Ledger file size
(Get-Item mesh\registry\ledger.json).Length / 1MB

# Account count
(Get-Content mesh\registry\ledger.json | ConvertFrom-Json).accounts.Count

# Transaction rate (from logs)
Select-String "credit\|debit" logs\*.log | Measure-Object
```

**Threshold:** If file > 1MB or save time > 100ms → Consider delta events

### Complexity Assessment

| Aspect | Rating | Notes |
|--------|--------|-------|
| **Implementation** | 🟡 MEDIUM | Event log + replay |
| **Migration** | 🟢 LOW | Can run in parallel |
| **Testing** | 🟡 MEDIUM | Replay correctness |
| **Rollback** | 🟢 EASY | Keep snapshot fallback |

### ROI Calculation

**Benefits:**
- Constant-time writes
- Audit trail (events)
- Faster saves

**Costs:**
- 4-6 hours implementation
- Event replay logic
- Snapshot pruning

**Verdict:** Implement if **ledger is bottleneck** (measure first)

---

## Feature 3: Async Health Probes

### Current: Sequential HTTP Pings
```python
for host in hosts:
    try:
        response = requests.get(f"{host}/health", timeout=1)
    except:
        mark_down(host)
```

### Proposed: Parallel Async Probes
```python
async def check_all_hosts(hosts):
    tasks = [check_host(host) for host in hosts]
    return await asyncio.gather(*tasks)
```

### When to Implement

**Implement if:**
- ✅ > 10 hosts to monitor
- ✅ Health check time > 10 seconds
- ✅ Slow failure detection is a problem

**Don't implement if:**
- ❌ < 5 hosts
- ❌ Health check time < 5 seconds
- ❌ Current speed is acceptable

### Metrics to Watch

```powershell
# Health check duration
Measure-Command { curl http://localhost:8001/api/system/health }

# Host count
(curl http://localhost:8001/api/system/health | ConvertFrom-Json).Count
```

**Threshold:** If check time > 10s or > 10 hosts → Consider async

### Complexity Assessment

| Aspect | Rating | Notes |
|--------|--------|-------|
| **Implementation** | 🟢 LOW | Simple async conversion |
| **Migration** | 🟢 EASY | Drop-in replacement |
| **Testing** | 🟢 LOW | Straightforward |
| **Rollback** | 🟢 EASY | Revert to sync |

### ROI Calculation

**Benefits:**
- Faster health checks
- Better responsiveness

**Costs:**
- 2-3 hours implementation
- Async complexity

**Verdict:** Implement if **many hosts** (>10), otherwise **defer**

---

## Feature 4: Fine-Grained Locking (or SQLite Migration)

### Current: Global File Locks
```python
with json_lock(filepath):
    # Entire file locked
    save_json(filepath, data)
```

### Proposed: Row-Level Locks (SQLite)
```sql
BEGIN IMMEDIATE;
UPDATE accounts SET balance = ? WHERE id = ?;
COMMIT;
```

### When to Implement

**Implement if:**
- ✅ High lock contention (>5% timeouts)
- ✅ Multiple concurrent writers
- ✅ Need parallel operations

**Don't implement if:**
- ❌ Lock timeout rate < 1%
- ❌ Single writer
- ❌ Current locking works

### Metrics to Watch

```powershell
# Lock timeout rate
$timeouts = Select-String "Lock timeout" logs\*.log
$operations = Select-String "persist_snapshot\|append_event" logs\*.log
Write-Host "Timeout rate: $($timeouts.Count / $operations.Count * 100)%"
```

**Threshold:** If timeout rate > 5% → Consider fine-grained locking

### Complexity Assessment

| Aspect | Rating | Notes |
|--------|--------|-------|
| **Implementation** | 🔴 HIGH | Full storage rewrite |
| **Migration** | 🔴 HIGH | Data migration critical |
| **Testing** | 🔴 HIGH | Concurrency edge cases |
| **Rollback** | 🔴 HARD | Significant changes |

### ROI Calculation

**Benefits:**
- Higher parallelism
- Lower contention

**Costs:**
- 6-8 hours implementation
- Migration risk
- New failure modes

**Verdict:** Implement only if **lock contention is severe** (>5% timeouts)

---

## Feature 5: Rotating Log Handlers

### Current: Append-Only Logs
```python
with open(log_path, "a") as f:
    f.write(event.to_json() + "\n")
```

### Proposed: Rotating Handlers
```python
handler = RotatingFileHandler(
    'state_transitions.jsonl',
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
```

### When to Implement

**Implement if:**
- ✅ Log files > 100MB
- ✅ Disk space concerns
- ✅ Log parsing becomes slow

**Don't implement if:**
- ❌ Log files < 50MB
- ❌ Plenty of disk space
- ❌ Logs are rotated externally

### Metrics to Watch

```powershell
# Log file sizes
Get-ChildItem logs\*.jsonl | Select-Object Name, @{Name='SizeMB';Expression={$_.Length/1MB}}
```

**Threshold:** If any log > 100MB → Consider rotation

### Complexity Assessment

| Aspect | Rating | Notes |
|--------|--------|-------|
| **Implementation** | 🟢 LOW | Simple handler swap |
| **Migration** | 🟢 EASY | No migration needed |
| **Testing** | 🟢 LOW | Standard library |
| **Rollback** | 🟢 EASY | Revert handler |

### ROI Calculation

**Benefits:**
- Bounded log sizes
- Easier log management

**Costs:**
- 1-2 hours implementation
- Minimal risk

**Verdict:** Implement if **log size is a problem**, otherwise **low priority**

---

## Decision Tree

```
Start
  │
  ├─ Running multiple workers? ────YES──> Implement SQLite Queue
  │                              NO
  │                               │
  ├─ Lock timeout rate > 5%? ────YES──> Investigate fine-grained locking
  │                              NO
  │                               │
  ├─ Ledger file > 1MB? ─────────YES──> Implement delta events
  │                              NO
  │                               │
  ├─ > 10 hosts to monitor? ─────YES──> Implement async health probes
  │                              NO
  │                               │
  ├─ Log files > 100MB? ─────────YES──> Implement log rotation
  │                              NO
  │                               │
  └─> Phase 2 not needed yet ────────> Continue with Phase 1
```

---

## Recommended Prioritization

### Tier 1: Implement if Needed
1. **SQLite Queue** - If scaling to multiple workers
2. **Ledger Delta Events** - If ledger is bottleneck

### Tier 2: Nice to Have
3. **Async Health Probes** - If many hosts
4. **Log Rotation** - If disk space concern

### Tier 3: Only if Critical
5. **Fine-Grained Locking** - Only if severe contention

---

## Phase 2 Readiness Checklist

Before implementing **any** Phase 2 feature:

- [ ] Phase 1 burn-in complete (72h)
- [ ] All Phase 1 metrics green
- [ ] Specific problem identified (not theoretical)
- [ ] Problem measured (not guessed)
- [ ] ROI calculated (benefit > cost)
- [ ] Rollback plan defined
- [ ] Tests written

**If any checkbox is unchecked → Don't implement**

---

## Summary Table

| Feature | Implement When | Priority | Complexity | ROI |
|---------|---------------|----------|------------|-----|
| SQLite Queue | Multiple workers | HIGH | HIGH | HIGH |
| Delta Events | Ledger bottleneck | MEDIUM | MEDIUM | MEDIUM |
| Async Probes | >10 hosts | LOW | LOW | LOW |
| Fine Locking | >5% timeouts | LOW | HIGH | LOW |
| Log Rotation | >100MB logs | LOW | LOW | LOW |

---

## Final Recommendation

**Current Status:** Phase 1 complete, system stable

**Next Steps:**
1. ✅ Run 72h burn-in test
2. ✅ Measure actual metrics
3. ⏸️ **Defer Phase 2** until metrics show need
4. ✅ Focus on business features

**Phase 2 is insurance, not requirement.**

---

**Decision Matrix Version:** 1.0  
**Review:** After Phase 1 burn-in  
**Update:** When scaling requirements change
