# Phase 1: Production Burn-In Test Plan

**Date:** 2026-01-13  
**Duration:** 24-72 hours  
**Goal:** Verify Phase 1 stability under real load before Phase 2

---

## Test Philosophy

**Not** chaos engineering (yet).  
**Not** property testing (yet).  
**Just** real-world operational validation.

---

## Test 1: Normal Load Baseline (24h)

### Setup
```bash
# Start complete system
.\START_COMPLETE_SYSTEM.bat

# Monitor logs
Get-Content logs\state_transitions.jsonl -Wait
Get-Content logs\worker.log -Wait
```

### Load Pattern
- Submit 10-20 jobs/hour (realistic workload)
- Mix of job types: `agent_plan`, `read_file`, `list_files`
- Let system run overnight

### Success Criteria
- [ ] No state corruption (verify `runtime/system_state.json`)
- [ ] All jobs complete (check `data/webrelay_in/`)
- [ ] No stale `.claimed` files (check `data/webrelay_out/`)
- [ ] Lock timeout warnings < 1% of transitions
- [ ] No failed reports (check `data/failed_reports/`)

### Metrics to Collect
```powershell
# Lock timeout rate
Select-String "Lock timeout" logs\*.log | Measure-Object

# Job latency (timestamp in job file vs result file)
# Manual spot check of 10 jobs

# Worker CPU usage
Get-Process -Name python | Select-Object CPU
```

---

## Test 2: Core Resilience (Network Failure)

### Scenario
Simulate Core API unavailability during job processing.

### Steps
```bash
# 1. Start system normally
.\START_COMPLETE_SYSTEM.bat

# 2. Submit 5 test jobs
for ($i=1; $i -le 5; $i++) {
    curl -X POST http://localhost:8001/api/missions/agent-plan `
         -H "Content-Type: application/json" `
         -d "{\"title\": \"Resilience Test $i\"}"
}

# 3. Kill Core API while jobs are processing
Stop-Process -Name "python" -Force  # (Core API process)

# 4. Wait 30 seconds

# 5. Restart Core API
cd core
python main.py

# 6. Check results
```

### Success Criteria
- [ ] Worker doesn't crash
- [ ] Jobs complete and write results
- [ ] Failed notifications saved to `data/failed_reports/`
- [ ] After Core restart, jobs sync successfully
- [ ] No duplicate job processing

### Verification
```powershell
# Check failed reports
Get-ChildItem data\failed_reports\*.failed_notify.txt

# Verify job results exist
Get-ChildItem data\webrelay_in\*.result.json

# Check for duplicate processing (no .claimed files left)
Get-ChildItem data\webrelay_out\*.claimed
```

---

## Test 3: Concurrent State Transitions

### Scenario
Trigger rapid state changes to test file locking.

### Steps
```bash
# 1. Start system
.\START_COMPLETE_SYSTEM.bat

# 2. Simulate rapid health changes
# Option A: Start/stop services rapidly
for ($i=1; $i -le 10; $i++) {
    # Stop WebRelay
    Stop-Process -Name "node" -Force
    Start-Sleep -Seconds 2
    
    # Restart WebRelay
    cd external\webrelay
    npm start
    Start-Sleep -Seconds 5
}

# Option B: Use API to force transitions
for ($i=1; $i -le 20; $i++) {
    curl -X POST http://localhost:8001/api/system/state/transition `
         -H "Content-Type: application/json" `
         -d '{"next_state": "DEGRADED", "reason": "Test transition"}'
    
    Start-Sleep -Milliseconds 100
    
    curl -X POST http://localhost:8001/api/system/state/transition `
         -H "Content-Type: application/json" `
         -d '{"next_state": "OPERATIONAL", "reason": "Test recovery"}'
}
```

### Success Criteria
- [ ] No corrupted `runtime/system_state.json`
- [ ] All transitions logged in `logs/state_transitions.jsonl`
- [ ] No duplicate transition IDs
- [ ] Lock timeout warnings < 5% (acceptable under stress)
- [ ] System recovers to correct state

### Verification
```powershell
# Validate JSON integrity
Get-Content runtime\system_state.json | ConvertFrom-Json

# Count transitions
Get-Content logs\state_transitions.jsonl | Measure-Object -Line

# Check for corruption (each line should be valid JSON)
Get-Content logs\state_transitions.jsonl | ForEach-Object {
    try { $_ | ConvertFrom-Json } catch { Write-Host "CORRUPT: $_" }
}

# Count lock timeouts
Select-String "Lock timeout" logs\*.log | Measure-Object
```

---

## Test 4: Watchdog Event Handling (Windows FS Edge Cases)

### Scenario
Test debounce and stability checks with rapid file operations.

### Steps
```bash
# 1. Start worker
cd worker
python worker_loop.py

# 2. Rapidly create job files (simulate burst)
for ($i=1; $i -le 50; $i++) {
    $jobId = [guid]::NewGuid().ToString()
    $job = @{
        job_id = $jobId
        kind = "list_files"
        payload = @{
            params = @{ root = "." }
        }
    } | ConvertTo-Json
    
    $job | Out-File "data\webrelay_out\$jobId.job.json" -Encoding UTF8
    Start-Sleep -Milliseconds 50  # Rapid burst
}

# 3. Monitor processing
Get-ChildItem data\webrelay_in\*.result.json | Measure-Object
```

### Success Criteria
- [ ] All 50 jobs processed exactly once
- [ ] No duplicate processing (check result count = 50)
- [ ] No stale `.claimed` files
- [ ] Worker log shows event-driven mode active
- [ ] Processing latency < 500ms per job

### Verification
```powershell
# Count results
$results = Get-ChildItem data\webrelay_in\*.result.json
Write-Host "Results: $($results.Count) (expected: 50)"

# Check for duplicates (should be none)
$claims = Get-ChildItem data\webrelay_out\*.claimed
Write-Host "Stale claims: $($claims.Count) (expected: 0)"

# Measure latency (spot check)
# Compare timestamps of .job.json vs .result.json
```

---

## Test 5: Reboot Recovery

### Scenario
Verify system recovers cleanly after ungraceful shutdown.

### Steps
```bash
# 1. Start system with active jobs
.\START_COMPLETE_SYSTEM.bat

# 2. Submit jobs
for ($i=1; $i -le 10; $i++) {
    curl -X POST http://localhost:8001/api/missions/agent-plan `
         -H "Content-Type: application/json" `
         -d "{\"title\": \"Recovery Test $i\"}"
}

# 3. Hard kill all processes (simulate crash)
Stop-Process -Name "python" -Force
Stop-Process -Name "node" -Force

# 4. Wait 10 seconds

# 5. Restart system
.\START_COMPLETE_SYSTEM.bat

# 6. Verify recovery
```

### Success Criteria
- [ ] State machine loads last valid state
- [ ] No corrupted state files
- [ ] Unclaimed jobs are picked up
- [ ] No duplicate processing
- [ ] System transitions to correct state based on health

### Verification
```powershell
# Check state integrity
Get-Content runtime\system_state.json | ConvertFrom-Json

# Verify last transition
Get-Content logs\state_transitions.jsonl | Select-Object -Last 1

# Check for orphaned jobs
Get-ChildItem data\webrelay_out\*.job.json
Get-ChildItem data\webrelay_out\*.claimed
```

---

## Monitoring Dashboard (Manual)

### Key Metrics to Track

**State Machine Health:**
```powershell
# Lock timeout rate
$timeouts = Select-String "Lock timeout" logs\*.log
$transitions = Get-Content logs\state_transitions.jsonl | Measure-Object -Line
Write-Host "Lock timeout rate: $($timeouts.Count / $transitions.Lines * 100)%"
```

**Worker Performance:**
```powershell
# Job throughput
$results = Get-ChildItem data\webrelay_in\*.result.json
Write-Host "Total jobs processed: $($results.Count)"

# Failed notifications
$failed = Get-ChildItem data\failed_reports\*.failed_notify.txt
Write-Host "Failed notifications: $($failed.Count)"
```

**System Stability:**
```powershell
# Stale claims (should be 0)
$claims = Get-ChildItem data\webrelay_out\*.claimed
Write-Host "Stale claims: $($claims.Count) (expected: 0)"

# State file integrity
try {
    Get-Content runtime\system_state.json | ConvertFrom-Json
    Write-Host "State file: OK"
} catch {
    Write-Host "State file: CORRUPTED"
}
```

---

## Success Thresholds

### Green Light for Phase 2
- ✅ Lock timeout rate < 1% (normal load)
- ✅ Lock timeout rate < 5% (stress test)
- ✅ Failed notification rate < 0.1%
- ✅ No state corruption
- ✅ No duplicate job processing
- ✅ Job latency < 500ms (p95)
- ✅ Worker CPU idle < 2%

### Yellow Light (Investigate)
- ⚠️ Lock timeout rate 1-5% (normal load)
- ⚠️ Failed notification rate 0.1-1%
- ⚠️ Occasional stale claims (< 5)
- ⚠️ Job latency 500-1000ms

### Red Light (Fix Before Phase 2)
- 🔴 Lock timeout rate > 5% (normal load)
- 🔴 Any state corruption
- 🔴 Duplicate job processing
- 🔴 Worker crashes
- 🔴 Failed notification rate > 1%

---

## Test Schedule

### Day 1 (24h)
- **Hour 0-1:** Test 1 setup + baseline
- **Hour 2:** Test 2 (Core resilience)
- **Hour 3:** Test 3 (Concurrent transitions)
- **Hour 4:** Test 4 (Watchdog burst)
- **Hour 5:** Test 5 (Reboot recovery)
- **Hour 6-24:** Normal load monitoring

### Day 2-3 (48h)
- Continue normal load
- Spot checks every 8 hours
- Collect metrics

### Day 3 (Final)
- Review all metrics
- Decision: Green/Yellow/Red
- Document findings

---

## Reporting Template

```markdown
# Phase 1 Burn-In Results

**Duration:** [X] hours  
**Status:** [Green/Yellow/Red]

## Metrics
- Lock timeout rate: [X]%
- Failed notifications: [X]
- State corruptions: [X]
- Duplicate jobs: [X]
- Avg job latency: [X]ms
- Worker CPU idle: [X]%

## Issues Found
1. [Issue description]
   - Severity: [Low/Medium/High]
   - Action: [Fix/Monitor/Accept]

## Recommendation
- [ ] Proceed to Phase 2
- [ ] Fix issues first
- [ ] Rollback Phase 1
```

---

**Test Plan Status:** Ready to execute  
**Estimated effort:** 1-2 hours active testing + 24-72h monitoring  
**Decision point:** After 72h or earlier if Red Light
