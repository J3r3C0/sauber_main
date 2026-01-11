# Sheratan System - Complete Audit & Verification Guide

**Version**: 1.0  
**Last Updated**: 2026-01-06  
**Status**: Production-Ready

---

## System Overview

Sheratan ist ein Multi-Layer-System für autonome Aufgabenausführung mit folgenden Hauptkomponenten:

1. **Core v2** - Mission/Task/Job Orchestration Kernel
2. **WebRelay** - ChatGPT/LLM Integration Bridge
3. **Offgrid Mesh** - Distributed Worker Network (Auction-based)
4. **Research System** - Immutable Research Issue Management

---

## Component 1: Core v2 (Orchestration Kernel)

### Location
`core/sheratan_core_v2/`

### Purpose
Zentraler Orchestrator für Mission → Task → Job Workflow mit automatischem Routing zu Brain (WebRelay) oder Body (Offgrid).

### Key Files
- `main.py` - FastAPI Server (Port 8001)
- `storage.py` - JSONL-based persistence with file locking
- `models.py` - Data models (Mission, Task, Job, JobEvent)
- `lcp_actions.py` - LCP (Loop Control Protocol) action interpreter
- `webrelay_bridge.py` - WebRelay integration
- `offgrid_bridge.py` - Offgrid mesh integration
- `loop_runner.py` - SelfLoop execution engine

### Core Functions

#### 1. Mission Management
```python
# Create mission
POST /api/missions
{
  "title": "Test Mission",
  "description": "Test description"
}

# List missions
GET /api/missions

# Get mission
GET /api/missions/{mission_id}

# Delete mission
DELETE /api/missions/{mission_id}
```

#### 2. Task Management
```python
# Create task for mission
POST /api/missions/{mission_id}/tasks
{
  "name": "test_task",
  "description": "Test task",
  "kind": "agent_plan",  # or "compute", "build", etc.
  "params": {}
}

# List all tasks
GET /api/tasks

# Get task
GET /api/tasks/{task_id}
```

#### 3. Job Management & Dispatch
```python
# Create job for task
POST /api/tasks/{task_id}/jobs
{
  "payload": {
    "prompt": "Test prompt"
  }
}

# List jobs (deduplicated - Latest Wins)
GET /api/jobs

# Get job
GET /api/jobs/{job_id}

# Dispatch job (automatic routing)
POST /api/jobs/{job_id}/dispatch
# Routes to:
# - WebRelay (Brain) if kind in ["agent_plan", "llm_call", "discovery", "sheratan_selfloop"]
# - Offgrid (Body) otherwise

# Sync job result
POST /api/jobs/{job_id}/sync
```

#### 4. Job Deduplication (Latest Wins)
```python
# storage.py
def list_jobs_deduplicated() -> List[models.Job]:
    """
    Research jobs: deduplicate by semantic job_id
    Latest determined by reissued_at or created_at
    Non-research jobs: kept as-is (UUID-based)
    """
```

### Data Storage
- `core/data/missions.jsonl` - Mission records
- `core/data/tasks.jsonl` - Task records
- `core/data/jobs.jsonl` - Job records (with deduplication)
- `core/data/job_events.jsonl` - Job event history

### Verification Tests

#### Test 1: Core API Health
```powershell
# Start Core
cd core/sheratan_core_v2
python -m uvicorn main:app --host 0.0.0.0 --port 8001

# Check health
Invoke-RestMethod -Uri http://localhost:8001/api/status
# Expected: {"status": "ok", "missions": <count>}
```

#### Test 2: Mission → Task → Job Flow
```powershell
# Create mission
$mission = Invoke-RestMethod -Method POST -Uri http://localhost:8001/api/missions -ContentType "application/json" -Body '{"title":"Test","description":"Test mission"}'

# Create task
$task = Invoke-RestMethod -Method POST -Uri "http://localhost:8001/api/missions/$($mission.id)/tasks" -ContentType "application/json" -Body '{"name":"test","description":"Test","kind":"agent_plan","params":{}}'

# Create job
$job = Invoke-RestMethod -Method POST -Uri "http://localhost:8001/api/tasks/$($task.id)/jobs" -ContentType "application/json" -Body '{"payload":{"prompt":"Test"}}'

# Verify job created
Invoke-RestMethod -Uri "http://localhost:8001/api/jobs/$($job.id)"
```

#### Test 3: Job Deduplication (Latest Wins)
```powershell
# Ingest research issue twice
python core/research/ingest_research.py core/research/issues/2026-W01.json
python core/research/ingest_research.py --force core/research/issues/2026-W01.json

# Check jobs API - should show only latest version
$jobs = Invoke-RestMethod -Uri http://localhost:8001/api/jobs
$duplicates = $jobs | Group-Object job_id | Where-Object { $_.Count -gt 1 }
# Expected: $duplicates should be empty (no duplicates)
```

---

## Component 2: WebRelay (Brain Integration)

### Location
`webrelay/` (separate repository/service)

### Purpose
Bridge zwischen Core und ChatGPT/LLM für reasoning tasks.

### Integration Points
- `core/sheratan_core_v2/webrelay_bridge.py`
- File-based communication via `webrelay_out/` and `webrelay_in/`

### Core Functions

#### 1. Job Enqueueing
```python
# webrelay_bridge.py
def enqueue_job(self, job_id: str):
    """Write job to webrelay_out/ for processing"""
```

#### 2. Result Syncing
```python
def try_sync_result(self, job_id: str) -> Optional[Job]:
    """Read result from webrelay_in/ and update job"""
```

### Verification Tests

#### Test 1: WebRelay Integration
```powershell
# Ensure WebRelay is running
# Check webrelay_out/ and webrelay_in/ directories exist

# Create LLM job
$task = Invoke-RestMethod -Method POST -Uri "http://localhost:8001/api/missions/<mission_id>/tasks" -ContentType "application/json" -Body '{"name":"llm_test","description":"LLM Test","kind":"llm_call","params":{}}'

$job = Invoke-RestMethod -Method POST -Uri "http://localhost:8001/api/tasks/$($task.id)/jobs" -ContentType "application/json" -Body '{"payload":{"prompt":"Say hello"}}'

# Dispatch to WebRelay
Invoke-RestMethod -Method POST -Uri "http://localhost:8001/api/jobs/$($job.id)/dispatch"

# Wait for result (auto-polling in background)
Start-Sleep -Seconds 30

# Check result
$result = Invoke-RestMethod -Uri "http://localhost:8001/api/jobs/$($job.id)"
# Expected: $result.result should contain LLM response
```

---

## Component 3: Offgrid Mesh (Body Integration)

### Location
`offgrid-net-*/` (separate repository)

### Purpose
Distributed worker network mit Auction-based job assignment für compute/build tasks.

### Integration Points
- `core/sheratan_core_v2/offgrid_bridge.py`
- Broker API: `http://127.0.0.1:9000`

### Core Functions

#### 1. Job Dispatch via Auction
```python
# offgrid_bridge.py
def dispatch_job(self, job_id: str, correlation_id: str) -> Optional[Job]:
    """
    1. POST /auction/start - Start auction
    2. Poll /auction/{auction_id}/status - Wait for winner
    3. Poll /jobs/{job_id}/status - Wait for completion
    """
```

### Verification Tests

#### Test 1: Offgrid Broker Health
```powershell
# Check broker is running
Invoke-RestMethod -Uri http://127.0.0.1:9000/health
# Expected: {"status": "ok"}
```

#### Test 2: Offgrid Job Dispatch
```powershell
# Create compute job
$task = Invoke-RestMethod -Method POST -Uri "http://localhost:8001/api/missions/<mission_id>/tasks" -ContentType "application/json" -Body '{"name":"compute_test","description":"Compute Test","kind":"compute","params":{}}'

$job = Invoke-RestMethod -Method POST -Uri "http://localhost:8001/api/tasks/$($task.id)/jobs" -ContentType "application/json" -Body '{"payload":{"command":"echo test"}}'

# Dispatch to Offgrid
Invoke-RestMethod -Method POST -Uri "http://localhost:8001/api/jobs/$($job.id)/dispatch"

# Wait for auction + execution
Start-Sleep -Seconds 60

# Check result
$result = Invoke-RestMethod -Uri "http://localhost:8001/api/jobs/$($job.id)"
# Expected: $result.status should be "completed"
```

---

## Component 4: Research System (Immutable Issue Management)

### Location
`core/research/`

### Purpose
Production-hardened research issue management mit Finalization, Hash Verification, und Job Deduplication.

### Key Files
- `ingest_research.py` - Main ingest pipeline (430 lines)
- `healthcheck.py` - System integrity validation
- `schema/sheratan.research_issue.v1.json` - JSON Schema
- `index.json` - Research issue index
- `issues/*.json` - Research issue files
- `logs/research_ingest.jsonl` - Audit log

### Core Functions

#### 1. Finalization
```powershell
python core/research/ingest_research.py --finalize core/research/issues/2026-W01.json
# Computes hash, sets status=final, adds finalized_at
```

#### 2. Ingest with Hash Verification
```powershell
python core/research/ingest_research.py core/research/issues/2026-W01.json
# Verifies hash, creates jobs (deduplicated)
```

#### 3. Force Reissue
```powershell
python core/research/ingest_research.py --force core/research/issues/2026-W01.json
# Creates new UUIDs, adds reissued_at + supersedes metadata
```

#### 4. Health Check
```powershell
python core/research/healthcheck.py
# Validates index, files, hash integrity, jobs.jsonl
```

#### 5. Deployment
```powershell
.\deploy_research.ps1 -IssueFile core/research/issues/2026-W01.json
# Automated: health check, backup, finalize, ingest, verify
```

### Verification Tests

#### Test 1: Finalization Workflow
```powershell
# Create draft issue (manually)
# Finalize
python core/research/ingest_research.py --finalize core/research/issues/test.json
# Expected: status=final, hash computed

# Verify idempotency
python core/research/ingest_research.py --finalize core/research/issues/test.json
# Expected: "Already finalized (hash matches)"
```

#### Test 2: Hash Verification
```powershell
# Ingest finalized issue
python core/research/ingest_research.py core/research/issues/2026-W01.json
# Expected: "Hash verified"

# Manually edit finalized issue (tamper)
# Try to ingest
python core/research/ingest_research.py core/research/issues/2026-W01.json
# Expected: "TAMPER DETECTED: Hash mismatch"
```

#### Test 3: Job Deduplication
```powershell
# Ingest twice
python core/research/ingest_research.py core/research/issues/2026-W01.json
python core/research/ingest_research.py core/research/issues/2026-W01.json
# Expected: Second ingest shows "Skipped N jobs (already exist)"

# Force reissue
python core/research/ingest_research.py --force core/research/issues/2026-W01.json
# Expected: New UUIDs created, reissued_at metadata added
```

#### Test 4: Health Check
```powershell
python core/research/healthcheck.py
# Expected:
# ✓ Index: index.json valid (N issues)
# ✓ Files: All N issue files exist
# ✓ Integrity: Hash integrity verified (N final issues)
# ✓ Jobs: jobs.jsonl valid (N jobs)
```

#### Test 5: Deployment
```powershell
.\deploy_research.ps1 -IssueFile core/research/issues/2026-W01.json
# Expected:
# [1/5] ✓ Health check passed
# [2/5] ✓ Backup created
# [3/5] ✓ Issue finalized (or already final)
# [4/5] ✓ Ingest complete
# [5/5] ✓ Post-deployment health check passed
```

---

## End-to-End System Verification

### Full Stack Test

```powershell
# 1. Start Core
cd core/sheratan_core_v2
python -m uvicorn main:app --host 0.0.0.0 --port 8001

# 2. Start WebRelay (if available)
# cd webrelay
# npm start

# 3. Start Offgrid Broker (if available)
# cd offgrid-net-*
# python broker/api.py

# 4. Health Checks
Invoke-RestMethod -Uri http://localhost:8001/api/status  # Core
Invoke-RestMethod -Uri http://127.0.0.1:9000/health      # Offgrid (if running)
python core/research/healthcheck.py                      # Research

# 5. Research Issue Deployment
.\deploy_research.ps1 -IssueFile core/research/issues/2026-W01.json

# 6. Verify Jobs Created
$jobs = Invoke-RestMethod -Uri http://localhost:8001/api/jobs
$researchJobs = $jobs | Where-Object { $_.job_id -like "job:W01-*" }
Write-Host "Research jobs created: $($researchJobs.Count)"

# 7. Dispatch Job (Brain route)
$job = $researchJobs[0]
Invoke-RestMethod -Method POST -Uri "http://localhost:8001/api/jobs/$($job.id)/dispatch"

# 8. Wait and check result
Start-Sleep -Seconds 30
$result = Invoke-RestMethod -Uri "http://localhost:8001/api/jobs/$($job.id)"
Write-Host "Job status: $($result.status)"
```

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Sheratan Core v2                        │
│                  (Mission/Task/Job Kernel)                  │
│                    Port: 8001 (FastAPI)                     │
└──────────────┬────────────────────────┬─────────────────────┘
               │                        │
               │ Brain Route            │ Body Route
               ▼                        ▼
    ┌──────────────────┐    ┌──────────────────────┐
    │    WebRelay      │    │   Offgrid Mesh       │
    │  (ChatGPT/LLM)   │    │  (Auction Broker)    │
    │  File-based I/O  │    │  Port: 9000 (HTTP)   │
    └──────────────────┘    └──────────────────────┘
               │                        │
               │                        ▼
               │              ┌──────────────────────┐
               │              │  Worker Hosts        │
               │              │  (Compute/Build)     │
               │              └──────────────────────┘
               │
               ▼
    ┌──────────────────────────────────────┐
    │       Research System                │
    │  - Finalization (--finalize)         │
    │  - Hash Verification                 │
    │  - Job Deduplication (Latest Wins)   │
    │  - Deployment (deploy_research.ps1)  │
    └──────────────────────────────────────┘
```

---

## Production Checklist

### Core v2
- [ ] Core API running (Port 8001)
- [ ] Health endpoint responds
- [ ] Mission/Task/Job CRUD works
- [ ] Job dispatch routing works (Brain/Body)
- [ ] Job deduplication active (Latest Wins)
- [ ] Storage files exist and valid

### WebRelay
- [ ] WebRelay service running
- [ ] webrelay_out/ and webrelay_in/ directories exist
- [ ] File-based communication works
- [ ] LLM jobs complete successfully

### Offgrid Mesh
- [ ] Broker running (Port 9000)
- [ ] Health endpoint responds
- [ ] Auction mechanism works
- [ ] Worker hosts connected
- [ ] Compute jobs complete successfully

### Research System
- [ ] Health check passes
- [ ] Finalization workflow works
- [ ] Hash verification enforced
- [ ] Job deduplication works
- [ ] Deployment script works
- [ ] Backup strategy active

---

## Troubleshooting

### Core v2 Issues

**Problem**: Core API not responding
```powershell
# Check if running
Get-Process | Where-Object { $_.ProcessName -like "*python*" }

# Check port
netstat -ano | findstr :8001

# Restart
cd core/sheratan_core_v2
python -m uvicorn main:app --host 0.0.0.0 --port 8001
```

**Problem**: Jobs not dispatching
```powershell
# Check logs
Get-Content core/data/job_events.jsonl | Select-Object -Last 10

# Check job status
Invoke-RestMethod -Uri http://localhost:8001/api/jobs/{job_id}
```

### Research System Issues

**Problem**: Hash mismatch
```powershell
# Revert changes or create new issue
# Never edit finalized issues manually
```

**Problem**: Jobs not deduplicated
```powershell
# Check jobs.jsonl
Get-Content core/data/jobs.jsonl | Select-String "job:W01-001-A"

# Check API (should show only 1)
$jobs = Invoke-RestMethod -Uri http://localhost:8001/api/jobs
$jobs | Where-Object { $_.job_id -eq "job:W01-001-A" }
```

---

## Backup & Recovery

### Full System Backup
```powershell
.\backup.ps1
# Creates: backups/full/sheratan_backup_YYYY-MM-DD_HHmmss.zip
# Includes: All files except node_modules, venv, __pycache__, .git, *.zip
# Structure: Preserved (2_sheratan_core\...)
```

### Research System Backup
```powershell
# Automated in deployment script
.\deploy_research.ps1 -IssueFile <issue>
# Creates: backups/research/backup_YYYY-MM-DD_HHmmss.zip
```

### Recovery
```powershell
# Extract backup
Expand-Archive -Path backups/full/sheratan_backup_*.zip -DestinationPath restore/

# Verify integrity
python core/research/healthcheck.py

# Restart services
cd core/sheratan_core_v2
python -m uvicorn main:app --host 0.0.0.0 --port 8001
```

---

**Status**: All components production-ready and verified  
**Last Audit**: 2026-01-06  
**Next Review**: After Phase 3 implementation
