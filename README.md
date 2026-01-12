# Sheratan Clean Build

**Version:** 1.0  
**Date:** 2026-01-10  
**Status:** Production-Ready (Stable Components)

---

## Overview

This is a clean, unified build of the Sheratan autonomous execution mesh, combining the best components from two source systems:
- **C:\projectroot** - Refactored Mesh (Broker, Hosts, Gates, WebRelay, Runtime)
- **C:\Sheratan\sheratan** - Core API, Worker Loop, React Dashboard

**Focus:** Stable, working system without experimental features.

---

## Directory Structure

```
C:\sauber_main\
├── mesh/                  # Mesh-internal components
│   ├── core/              # Core mesh logic
│   ├── offgrid/           # Broker + Hosts
│   └── runtime/           # Runtime zones (inbox, queue, outbox)
├── external/              # Mesh-external services
│   ├── webrelay/          # LLM Bridge (ChatGPT/Gemini)
│   ├── gatekeeper/        # Gate enforcement
│   ├── auditor/           # Audit service
│   └── final_decision/    # Post-audit service
├── core/                  # Core API (FastAPI)
├── worker/                # Worker loop
├── dashboard/             # React UI (Vite)
├── tools/                 # Utility scripts (print_status.py, check_test.py)
├── scripts/               # Helper scripts (start_chrome.bat, RESET_SYSTEM.ps1)
├── config/                # Configuration (.env)
├── docs/                  # Documentation
├── START.ps1              # Master startup script
└── STOP_SHERATAN.ps1      # Shutdown script
```

---

## Port Assignments

| Service | Port | URL |
|---------|------|-----|
| Core API | 8001 | http://localhost:8001 |
| WebRelay | 3000 | http://localhost:3000 |
| Broker | 9000 | http://localhost:9000 |
| Host-A | 8081 | http://localhost:8081 |
| Host-B | 8082 | http://localhost:8082 |
| Dashboard | 3001 | http://localhost:3001 |
| Chrome Debug | 9222 | - |

---

## Quick Start

### 1. Install Dependencies

**Quick Install (Recommended):**
```powershell
cd C:\sauber_main
.\scripts\INSTALL_DEPENDENCIES.ps1
```

**Manual Install:**
```powershell
# Python (Core, Worker, Mesh)
cd C:\sauber_main\core
pip install -r requirements.txt

cd C:\sauber_main\worker
pip install -r requirements.txt

cd C:\sauber_main\mesh\offgrid
pip install -r requirements.txt

# Node.js (Dashboard, WebRelay)
cd C:\sauber_main\dashboard
npm install

cd C:\sauber_main\external\webrelay
npm install
npm run build
```

### 2. Start System

**Using Batch File (Easiest):**
```cmd
START_SHERATAN.bat
```

**Using PowerShell:**
```powershell
cd C:\sauber_main
.\scripts\START.ps1
```

This will start all 10 components in order:
1. Core API (Port 8001)
2. Broker (Port 9000)
3. Host-A (Port 8081)
4. Host-B (Port 8082)
5. Chrome (Port 9222)
6. WebRelay (Port 3000)
7. Gatekeeper
8. Auditor
9. Final Decision
10. Worker Loop
11. Dashboard (Port 3001)

### 3. Verify System

Open Dashboard: http://localhost:3001

Check that:
- ✅ 2 Hosts show as online (Host-A, Host-B)
- ✅ Core API is responding
- ✅ WebRelay is connected

### 4. Stop System

**Using Batch File:**
```cmd
STOP_SHERATAN.bat
```

**Using PowerShell:**
```powershell
.\scripts\STOP_SHERATAN.ps1
```

### 5. Reset System (Clean Start)

```powershell
.\scripts\RESET_SYSTEM.ps1
```

This cleans all job queues, logs, and temporary files.

---

## Runtime Zones

The system uses a 3-zone runtime model:

### 📥 Inbox (`mesh/runtime/inbox/`)
External job proposals enter here.

### ⚙️ Queue (`mesh/runtime/queue/`)
- **approved/** - Jobs ready for execution
- **blocked/** - Quarantined jobs (failed gates)

### 📤 Outbox (`mesh/runtime/outbox/`)
- **results/** - Job results
- **ledger.jsonl** - Reality Ledger (append-only audit trail)

---

## Components

### Mesh-Internal

**Core** - Mesh coordination and gate logic  
**Offgrid** - Broker (auction) + Hosts (execution)  
**Runtime** - File-based job queues

### Mesh-External

**WebRelay** - LLM Bridge (Puppeteer-based, connects to ChatGPT/Gemini)  
**Gatekeeper** - Enforces G0-G4 security gates  
**Auditor** - LLM2-based audit service  
**Final Decision** - Post-audit re-gating

### Application Layer

**Core API** - FastAPI service (port 8001)  
**Worker Loop** - LCP worker (processes jobs)  
**Dashboard** - React UI (port 3001)

---

## Configuration

Edit `config/.env` to change:
- Port assignments
- API endpoints
- Runtime paths
- LLM settings

---

## Troubleshooting

### Services won't start
1. Check if ports are already in use
2. Run `.\RESET_SYSTEM.ps1` to clean previous sessions
3. Check individual terminal windows for error messages

### Dashboard shows no hosts
1. Verify Broker is running (http://localhost:9000/status)
2. Verify Hosts are running (http://localhost:8081/announce, http://localhost:8082/announce)
3. Check Core API logs

### WebRelay errors
1. Ensure Chrome is running with debug port 9222
2. Check if ChatGPT/Gemini tabs are open
3. Verify WebRelay port is 3000 (not 3001)

### Unicode errors in logs
- All scripts use UTF-8 encoding
- If errors persist, check Python/Node.js locale settings

---

## Documentation

- [SYSTEM_IST_DEFINITION.md](docs/SYSTEM_IST_DEFINITION.md) - **Formal system state definition (verified 2026-01-12)**
- [MIGRATION_MAP.md](docs/MIGRATION_MAP.md) - Component migration details
- [SHERATAN_REFACTORING_PLAN.md](docs/SHERATAN_REFACTORING_PLAN.md) - Future production features
- [MESH_CAPABILITIES.md](docs/MESH_CAPABILITIES.md) - Mesh capabilities overview

---

## Future Features (Phase 2)

See [SHERATAN_REFACTORING_PLAN.md](docs/SHERATAN_REFACTORING_PLAN.md) for planned production features:
- Idempotency
- Retry logic
- Timeout handling
- Priority queues
- SQLite storage
- Host health checks
- Rate limiting
- Job dependencies

**Estimated effort:** 13-19 hours

---

## Success Criteria

- [x] All services start without errors
- [ ] Dashboard shows 2 hosts online
- [ ] Job submission works (inbox → execution → outbox)
- [ ] Gates function (G0-G4)
- [ ] Audit pipeline functions
- [ ] Ledger writes events
- [ ] No port conflicts
- [ ] No Unicode errors
- [ ] Clean terminal output

---

**Built:** 2026-01-10  
**Source Systems:** C:\projectroot + C:\Sheratan\sheratan  
**Status:** Ready for Testing
