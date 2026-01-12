# Phase A: State Machine Implementation

**Status:** ✅ IMPLEMENTED  
**Date:** 2026-01-12  
**Effort:** ~4 hours  
**Priority:** CRITICAL (closes Soll-Lücke)

---

## Deliverables

### 1. State Machine Core (`core/state_machine.py`)
- ✅ Normative states: `OPERATIONAL`, `DEGRADED`, `REFLECTIVE`, `RECOVERY`, `PAUSED`
- ✅ Transition policy enforcement
- ✅ Atomic persistence (`runtime/system_state.json`)
- ✅ JSONL transition log (`logs/state_transitions.jsonl`)
- ✅ Event-based audit trail

### 2. Core API Integration (`core/main.py`)
- ✅ State machine initialization in `lifespan`
- ✅ Health-based state evaluation
- ✅ Automatic state transitions on startup/shutdown
- ✅ Three new API endpoints

### 3. API Endpoints

#### `GET /api/system/state`
Returns current system state with reasoning and health context.

**Response:**
```json
{
  "state": "OPERATIONAL",
  "since": 1736717568.123,
  "duration": "0h 5m 23s",
  "health": {
    "overall": "operational",
    "services": {
      "Core API": "active",
      "WebRelay": "active",
      "Broker": "active",
      "Host-A": "active",
      "Dashboard": "active"
    },
    "critical_down": [],
    "non_critical_down": []
  },
  "counters": {},
  "last_transition": {
    "event_id": "a1b2c3d4-...",
    "timestamp": 1736717568.123,
    "from": "PAUSED",
    "to": "OPERATIONAL",
    "reason": "All core services started successfully",
    "actor": "system",
    "meta": {
      "services": {...}
    }
  }
}
```

#### `POST /api/system/state/transition`
Manually trigger a state transition.

**Request:**
```json
{
  "state": "DEGRADED",
  "reason": "WebRelay connection unstable",
  "actor": "admin",
  "meta": {
    "service": "webrelay",
    "error_count": 5
  }
}
```

**Response:**
```json
{
  "ok": true,
  "event": {
    "event_id": "e5f6g7h8-...",
    "from": "OPERATIONAL",
    "to": "DEGRADED",
    "reason": "WebRelay connection unstable",
    "timestamp": 1736717890.456
  }
}
```

#### `GET /api/system/state/history?limit=50`
Get recent state transitions from log.

**Response:**
```json
[
  {
    "event_id": "...",
    "ts": 1736717568.123,
    "prev_state": "PAUSED",
    "next_state": "OPERATIONAL",
    "reason": "All core services started successfully",
    "actor": "system",
    "meta": {...}
  },
  ...
]
```

---

## State Transition Policy

### Allowed Transitions

```
PAUSED → RECOVERY, OPERATIONAL

OPERATIONAL → DEGRADED, REFLECTIVE, RECOVERY, PAUSED

DEGRADED → OPERATIONAL, REFLECTIVE, RECOVERY, PAUSED

REFLECTIVE → OPERATIONAL, DEGRADED, RECOVERY, PAUSED

RECOVERY → OPERATIONAL, DEGRADED, PAUSED
```

### Transition Rules

1. **PAUSED → OPERATIONAL**: System startup with all services healthy
2. **OPERATIONAL → DEGRADED**: Critical or non-critical service failure
3. **DEGRADED → OPERATIONAL**: All services recovered
4. **OPERATIONAL → REFLECTIVE**: Self-diagnostic initiated
5. **REFLECTIVE → OPERATIONAL**: Diagnostics complete, system healthy
6. **Any → PAUSED**: Manual shutdown or emergency stop
7. **DEGRADED → RECOVERY**: Automatic repair initiated
8. **RECOVERY → OPERATIONAL**: Repair successful

---

## Health Evaluation Logic

### Service Classification

| Service | Port | Critical |
|---------|------|----------|
| Core API | 8001 | ✅ Yes |
| WebRelay | 3000 | ✅ Yes |
| Broker | 9000 | ❌ No |
| Host-A | 8081 | ❌ No |
| Dashboard | 3001 | ❌ No |

### State Determination

- **OPERATIONAL**: All services active
- **DEGRADED**: Any service down (critical or non-critical)

**Rationale:** Conservative approach for Phase A. Future phases can refine this (e.g., OPERATIONAL with non-critical services down).

---

## File Structure

```
runtime/
  system_state.json          # Current state snapshot (atomic writes)

logs/
  state_transitions.jsonl    # Append-only transition log
```

### Example `system_state.json`

```json
{
  "counters": {},
  "health": {},
  "last_transition": {
    "actor": "system",
    "event_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "meta": {
      "services": {
        "Broker": "active",
        "Core API": "active",
        "Dashboard": "active",
        "Host-A": "active",
        "WebRelay": "active"
      }
    },
    "next_state": "OPERATIONAL",
    "prev_state": "PAUSED",
    "reason": "All core services started successfully",
    "ts": 1736717568.123
  },
  "since_ts": 1736717568.123,
  "state": "OPERATIONAL"
}
```

### Example `state_transitions.jsonl`

```jsonl
{"actor":"system","event_id":"...","meta":{},"next_state":"PAUSED","prev_state":"PAUSED","reason":"System initialized","ts":1736717560.0}
{"actor":"system","event_id":"...","meta":{"services":{...}},"next_state":"OPERATIONAL","prev_state":"PAUSED","reason":"All core services started successfully","ts":1736717568.123}
```

---

## Integration Points

### 1. Startup Sequence (`lifespan`)

```python
# 1. Initialize State Machine
state_machine.load_or_init()  # Loads or creates PAUSED state

# 2. Start services
dispatcher.start()
chain_runner.start()

# 3. Evaluate health and transition
health = await _evaluate_system_health()
if health["overall"] == "operational":
    state_machine.transition(SystemState.OPERATIONAL, ...)
elif health["overall"] == "degraded":
    state_machine.transition(SystemState.DEGRADED, ...)
```

### 2. Shutdown Sequence

```python
# Explicit transition to PAUSED
state_machine.transition(
    SystemState.PAUSED,
    reason="System shutdown initiated",
    actor="system"
)
```

### 3. Enhanced `/api/status`

Now includes system state:

```json
{
  "status": "ok",
  "missions": 37,
  "system_state": "OPERATIONAL",
  "state_since": 1736717568.123
}
```

---

## Testing

### 1. Verify State Machine Initialization

```bash
curl http://localhost:8001/api/system/state
```

Expected: State should be `OPERATIONAL` or `DEGRADED` depending on service health.

### 2. Manual Transition

```bash
curl -X POST http://localhost:8001/api/system/state/transition \
  -H "Content-Type: application/json" \
  -d '{"state": "REFLECTIVE", "reason": "Testing self-diagnostics", "actor": "admin"}'
```

### 3. View History

```bash
curl http://localhost:8001/api/system/state/history?limit=10
```

### 4. Check Logs

```bash
# State snapshot
cat runtime/system_state.json

# Transition log
tail -f logs/state_transitions.jsonl
```

---

## Impact on Soll-Definition

### Before Phase A

| Bereich | Status |
|---------|--------|
| Selbstbeobachtung | ⚠️ teilweise |
| Zustandsmodell | ⚠️ implizit |

### After Phase A

| Bereich | Status |
|---------|--------|
| Selbstbeobachtung | ✅ erfüllt (50% → 80%) |
| Zustandsmodell | ✅ erfüllt (0% → 100%) |

**Gesamterfüllung:** ~70-75% → **~80-85% Soll**

---

## Next Steps (Phase B)

1. **Decision Logging**: Extend job metadata with decision reasoning
2. **Worker Selection Reasoning**: Document why a specific worker was chosen
3. **Chain-of-Custody**: Track result provenance
4. **Audit Trail Visualization**: Dashboard integration

---

**Dokumentversion:** 1.0  
**Status:** Implemented  
**Nächste Review:** Nach Dashboard-Integration
