# Sheratan Core - Production Backup
**Created:** 2026-01-04_07-33-32
**Status:** Production-Ready System

## 📦 Contents

### Core System
- \core/sheratan_core_v2/\ - Main FastAPI application
- \core/lcp/\ - LCP validators (Core2 + Self-Loop)
- \worker/\ - Job worker with Self-Loop support

### Dashboards
- \dashboards/Visual Workflow Diagram/\ - 3D Architecture Visualization
- \eact-dashboard/\ - Operations Dashboard
- \dashboards/*.html\ - Static HTML dashboards

### WebRelay
- \webrelay/\ - LLM bridge service

### Documentation
- \docs/\ - System documentation
- \*.md\ - Root documentation files
- \rain_artifacts/\ - Complete session documentation

### Scripts
- \*.ps1\ - PowerShell startup scripts
- \*.bat\ - Batch startup scripts

## 🚀 Quick Start

### 1. Install Dependencies

**Core:**
\\\ash
cd core/sheratan_core_v2
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
\\\

**Visual Dashboard:**
\\\ash
cd dashboards/Visual\ Workflow\ Diagram
npm install
\\\

**React Dashboard:**
\\\ash
cd react-dashboard
npm install
\\\

### 2. Start Services

**Core:**
\\\ash
cd core
.\venv\Scripts\Activate.ps1
python -m sheratan_core_v2.main
\\\

**Dashboards:**
\\\ash
# Visual Workflow
cd dashboards/Visual\ Workflow\ Diagram
npm run dev  # localhost:3000

# React Operations
cd react-dashboard
npm run dev  # localhost:5174
\\\

## ✅ System Status

**Components:**
- ✅ Offgrid Memory Integration (100%)
- ✅ LCP Validation (20 tests passing)
- ✅ Self-Loop System (100% - Worker integrated!)
- ✅ Visual Workflow Dashboard (100%)
- ✅ React Operations Dashboard (100%)

**Total Completion:** 100% Production Ready!

## 📊 Features

### Backend
- FastAPI Core on port 8001
- SQLite storage
- Mission/Task/Job lifecycle
- WebRelay bridge
- LCP action interpreter
- Self-Loop API endpoints
- Offgrid Memory integration

### Self-Loop System
- Collaborative co-thinking
- A/B/C/D Markdown format
- Automatic iteration
- Loop state tracking
- Worker integration complete

### Dashboards
- 3D interactive architecture visualization
- Real-time mission management
- Job queue monitoring
- LLM console
- Self-Loop mode toggle

## 📝 Documentation

See \rain_artifacts/\ for complete session documentation:
- \inal_walkthrough.md\ - Complete system overview
- \system_architecture.md\ - Architecture diagram
- \worker_selfloop_integration.md\ - Worker integration guide
- \isual_dashboard_guide.md\ - Dashboard usage guide
- \selfloop_test_guide.md\ - Testing instructions

## 🎯 Next Steps

1. Install dependencies (see Quick Start)
2. Configure \.env\ files
3. Start services
4. Access dashboards
5. Create first Self-Loop mission!

---

**Backup Created:** 2026-01-04_07-33-32  
**System Version:** Sheratan Core v2  
**Status:** ⭐⭐⭐⭐⭐ Production Ready
