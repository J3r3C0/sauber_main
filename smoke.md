# Smoke Checklist – PASS/FAIL

## G1 Boot/Health ✅ PASS
- [x] Run START_COMPLETE_SYSTEM.bat
- [x] GET /api/system/health returns HTTP 200 (repeat 3x)
- [x] No unhandled exceptions in logs (first 60s)
**Evidence:** 
- BASE_URL discovered: `http://localhost:8001`
- Status codes: 200, 200, 200, 200 (4x consecutive)
- Timestamp: 2026-01-14T02:37:33Z
- Response: JSON array with service statuses (core-api, webrelay, broker, host-a, dashboard)

## G2 E2E Job ✅ PASS
- [x] POST /api/jobs read_file core/main.py (via chain spec)
- [x] Response indicates success (job created)
- [x] Dispatcher picks up job (moved to working)
**Evidence:**
- **Root Cause:** Jobs had invalid `depends_on: ['parent']` (orphaned)
- **Fix:** Cleared invalid dependencies for 5 jobs
- **Result:** Dispatcher ACTIVE - 3 jobs moved to working
- **Dispatcher Logs:** 
  - `[dispatcher] thread launched`
  - `[dispatcher] Central loops started.`
  - `[dispatcher] is_running=True`
  - `[dispatcher] 🚀 Dispatching job...` (after fix)

## G3 Failure/Recovery (pick one)
- [ ] Failure visible
- [ ] Restart/retry recovers cleanly
- [ ] No stuck locks/leases
- [ ] No duplicate claim/processing
Evidence: scenario + steps + final proof
