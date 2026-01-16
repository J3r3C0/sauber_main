# System Stabilization Plan - Port 8001

## Ground Truth
- **Start Script:** `START_COMPLETE_SYSTEM.bat`
- **Core Port:** 8001
- **Known Endpoints:** `/api/system/health`, `/api/jobs`
- **Constraint:** Base URL must be discovered (docs inconsistent)

---

## Phase 1: PLAN

### 1.1 System Start
```powershell
# Command
.\START_COMPLETE_SYSTEM.bat

# Expected
- Core starts on port 8001
- Logs show "Application startup complete"
- No unhandled exceptions in first 60s
```

### 1.2 URL Discovery Strategy
**Candidate Base URLs for port 8001:**
1. `http://localhost:8001`
2. `http://127.0.0.1:8001`

**Discovery Steps:**
```bash
# Test 1
curl -s -o /dev/null -w "%{http_code}" http://localhost:8001/api/system/health

# Test 2
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8001/api/system/health

# Select first 200 as BASE_URL
```

### 1.3 Evidence Capture
**G1 Boot/Health:**
- HTTP status codes (3x health checks)
- Response body structure
- Log excerpt (startup + first 60s)
- Timestamp of successful health check

**G2 E2E Job:**
- Request payload
- Response body (job_id, status, result)
- Job completion proof (status=completed or ok=true)
- Content verification (file exists in response)

**G3 Failure/Recovery:**
- Scenario: Worker kill during job processing
- Evidence: job status before/after, lock state, no duplicates

---

## Phase 2: EXECUTE / VERIFY

### Gate 1: Boot & URL Discovery
**Steps:**
1. Start system via `START_COMPLETE_SYSTEM.bat`
2. Wait 10s for startup
3. Probe health endpoints
4. Select BASE_URL
5. Verify 3x consecutive 200 responses
6. Check logs for exceptions

**Success Criteria:**
- ✅ HTTP 200 from health endpoint
- ✅ No exceptions in logs
- ✅ BASE_URL discovered and stable

---

### Gate 2: E2E Job
**Request:**
```bash
curl -X POST {BASE_URL}/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "kind": "read_file",
    "params": {"path": "core/main.py"}
  }'
```

**Success Criteria:**
- ✅ HTTP 200/201 response
- ✅ Response contains `job_id`
- ✅ Job completes with `status=completed` or `ok=true`
- ✅ Result contains file content
- ✅ Single claim (no duplicates)

---

### Gate 3: Failure/Recovery
**Scenario:** Simulate worker failure during job

**Steps:**
1. Submit long-running job
2. Kill worker process mid-execution
3. Restart worker
4. Verify job recovers or fails cleanly
5. Check no stuck locks
6. Verify no duplicate processing

**Success Criteria:**
- ✅ Failure detected
- ✅ Recovery completes
- ✅ No stuck locks/leases
- ✅ No duplicate claims

---

## Phase 3: FIX-LOOP
If any gate fails:
1. Identify root cause
2. Apply minimal patch
3. Re-run failed gate
4. Repeat until PASS

---

## Phase 4: FINALIZE
**Report Format:**
```
Gate 1: PASS/FAIL
Evidence: [status codes, timestamps, logs]

Gate 2: PASS/FAIL
Evidence: [request, response, job_id]

Gate 3: PASS/FAIL
Evidence: [scenario, recovery proof]

Files Changed: [list]
Remaining Risks: [max 5]
Next Steps: [hardening recommendations]
```
