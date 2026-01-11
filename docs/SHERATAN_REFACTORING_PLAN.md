# Sheratan Mesh - Production-Ready Refactoring Plan

**Version:** 2.0  
**Datum:** 2026-01-10  
**Status:** Design-Phase

---

## Executive Summary

Dieser Plan beschreibt die Umstrukturierung von Sheratan zu einem production-ready, sicheren und skalierbaren autonomen Execution-Mesh. Das Refactoring umfasst:

1. **Architektur-Vereinfachung** - Von 6 Zonen zu 3 klaren Bereichen
2. **Production-Features** - Idempotenz, Retry, Timeouts, Prioritäten
3. **Klare Mesh-Grenze** - Trennung von Mesh-intern und extern
4. **Bessere Skalierbarkeit** - SQLite + Dateisystem statt nur Files

---

## 1. Ziel-Architektur

### 1.1 Verzeichnisstruktur

```
c:\projectroot\
│
├── mesh/                          # 🔒 MESH-INTERN (geschlossenes System)
│   ├── core/                      # Mesh-Gehirn (API, Storage, Gates)
│   │   ├── api/                   # FastAPI Endpoints (Mesh I/O Interface)
│   │   │   ├── __init__.py
│   │   │   ├── jobs.py            # Job-Endpoints
│   │   │   ├── missions.py        # Mission-Endpoints
│   │   │   └── health.py          # Health/Status
│   │   │
│   │   ├── gates/                 # G0-G4 Security Gates
│   │   │   ├── __init__.py
│   │   │   ├── gate_g0_barrier.py
│   │   │   ├── gate_g1_payload.py
│   │   │   ├── gate_g2_resource.py
│   │   │   ├── gate_g3_capability.py
│   │   │   └── gate_g4_policy.py
│   │   │
│   │   ├── storage/               # Job/Task/Mission Storage
│   │   │   ├── __init__.py
│   │   │   ├── database.py        # SQLite Connection
│   │   │   ├── models.py          # Data Models
│   │   │   └── migrations/        # DB Schema Migrations
│   │   │
│   │   ├── dispatcher.py          # Job Routing Logic
│   │   ├── rate_limiter.py        # Rate Limiting
│   │   ├── retry_handler.py       # Retry Logic
│   │   └── main.py                # Core Startup
│   │
│   ├── offgrid/                   # Mesh-Körper (Execution Network)
│   │   ├── broker/                # Auction & Job Distribution
│   │   │   ├── auction_api.py
│   │   │   └── auction_logic.py
│   │   │
│   │   ├── host/                  # Worker Node Daemon
│   │   │   ├── api_real.py
│   │   │   ├── executor.py
│   │   │   └── heartbeat.py
│   │   │
│   │   └── discovery/             # Host Discovery (future)
│   │       └── __init__.py
│   │
│   └── runtime/                   # Mesh-Daten (3-Zonen-System)
│       ├── inbox/                 # 📥 INPUT: External proposals
│       │   └── *.json
│       │
│       ├── queue/                 # ⚙️ PROCESSING: Internal queue
│       │   ├── approved/          # Ready for execution
│       │   └── blocked/           # Quarantined jobs
│       │
│       └── outbox/                # 📤 OUTPUT: Results & ledger
│           ├── results/           # Job results
│           └── ledger.jsonl       # Reality Ledger (append-only)
│
├── external/                      # 🌐 MESH-EXTERN (außerhalb der Grenze)
│   ├── webrelay/                  # LLM Bridge (ChatGPT/Gemini)
│   │   ├── api.ts
│   │   ├── backends/
│   │   └── package.json
│   │
│   ├── auditor/                   # LLM2 Audit Service
│   │   └── auditor_relay.py
│   │
│   ├── gatekeeper/                # Gate Enforcement Service
│   │   └── gatekeeper.py
│   │
│   └── final_decision/            # Post-Audit Re-Gate Service
│       └── final_decision.py
│
├── tools/                         # 🛠️ UTILITIES (Development)
│   ├── update_lock.py
│   ├── sanitize_unicode.py
│   └── test_*.py
│
├── config/                        # ⚙️ CONFIGURATION
│   ├── default-config.json
│   └── .env
│
├── docs/                          # 📚 DOCUMENTATION
│   ├── ARCHITECTURE.md
│   ├── API.md
│   └── GATES.md
│
├── dashboard.html                 # 🖥️ UI
├── START_SHERATAN.ps1             # 🚀 Master Startup
└── README.md
```

### 1.2 Datenmodelle (Production-Ready)

```python
# mesh/core/storage/models.py

from enum import Enum
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class JobStatus(str, Enum):
    PENDING = "pending"           # Wartet auf Dispatch
    RUNNING = "running"           # Wird gerade ausgeführt
    COMPLETED = "completed"       # Erfolgreich abgeschlossen
    FAILED = "failed"             # Fehlgeschlagen
    QUARANTINED = "quarantined"   # Blockiert durch Gates
    THROTTLED = "throttled"       # Rate-Limited


class JobPriority(int, Enum):
    CRITICAL = 0   # Sofort ausführen
    HIGH = 1       # Innerhalb 1 Minute
    NORMAL = 2     # Innerhalb 5 Minuten
    LOW = 3        # Wenn Ressourcen verfügbar


class Job(BaseModel):
    # Identity
    id: str                           # UUID
    idempotency_key: str              # Für Deduplication
    
    # Metadata
    source: str                       # "narrative", "input", etc.
    created_at: datetime
    updated_at: datetime
    
    # Execution
    status: JobStatus
    priority: JobPriority = JobPriority.NORMAL
    timeout_seconds: int = 300        # 5 Minuten default
    
    # Retry
    max_retries: int = 3
    retry_count: int = 0
    retry_backoff: str = "exponential"  # "exponential" or "linear"
    last_retry_at: Optional[datetime] = None
    
    # Dependencies
    depends_on: List[str] = []        # Job IDs
    
    # Payload
    task_id: str
    mission_id: str
    payload: Dict[str, Any]
    
    # Result
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    # Audit
    gate_decisions: List[Dict[str, Any]] = []
    audit_decision: Optional[Dict[str, Any]] = None
    executed_by: Optional[str] = None  # Host ID
    execution_started_at: Optional[datetime] = None
    execution_completed_at: Optional[datetime] = None


class HostStatus(str, Enum):
    ONLINE = "online"
    BUSY = "busy"
    OFFLINE = "offline"


class Host(BaseModel):
    id: str
    status: HostStatus
    last_heartbeat: datetime
    capabilities: List[str] = []      # ["python", "docker", "gpu"]
    current_jobs: List[str] = []      # Job IDs currently running
    max_concurrent: int = 5           # Max parallel jobs
    
    
class RateLimitConfig(BaseModel):
    source: str
    max_jobs_per_minute: int = 10
    max_concurrent_jobs: int = 5
    current_count: int = 0
    window_start: datetime
```

### 1.3 Datenbank-Schema (SQLite)

```sql
-- mesh/core/storage/migrations/001_initial.sql

-- Jobs Table
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    idempotency_key TEXT UNIQUE NOT NULL,
    source TEXT NOT NULL,
    status TEXT NOT NULL,
    priority INTEGER NOT NULL DEFAULT 2,
    timeout_seconds INTEGER NOT NULL DEFAULT 300,
    max_retries INTEGER NOT NULL DEFAULT 3,
    retry_count INTEGER NOT NULL DEFAULT 0,
    retry_backoff TEXT NOT NULL DEFAULT 'exponential',
    depends_on TEXT,  -- JSON array of job IDs
    task_id TEXT NOT NULL,
    mission_id TEXT NOT NULL,
    payload TEXT NOT NULL,  -- JSON
    result TEXT,  -- JSON
    error TEXT,
    gate_decisions TEXT,  -- JSON array
    audit_decision TEXT,  -- JSON
    executed_by TEXT,
    created_at TIMESTAMP NOT NULL,
    updated_at TIMESTAMP NOT NULL,
    execution_started_at TIMESTAMP,
    execution_completed_at TIMESTAMP,
    last_retry_at TIMESTAMP
);

CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_priority ON jobs(priority);
CREATE INDEX idx_jobs_created_at ON jobs(created_at);
CREATE INDEX idx_jobs_idempotency_key ON jobs(idempotency_key);

-- Hosts Table
CREATE TABLE hosts (
    id TEXT PRIMARY KEY,
    status TEXT NOT NULL,
    last_heartbeat TIMESTAMP NOT NULL,
    capabilities TEXT,  -- JSON array
    current_jobs TEXT,  -- JSON array
    max_concurrent INTEGER NOT NULL DEFAULT 5
);

CREATE INDEX idx_hosts_status ON hosts(status);
CREATE INDEX idx_hosts_last_heartbeat ON hosts(last_heartbeat);

-- Rate Limits Table
CREATE TABLE rate_limits (
    source TEXT PRIMARY KEY,
    max_jobs_per_minute INTEGER NOT NULL DEFAULT 10,
    max_concurrent_jobs INTEGER NOT NULL DEFAULT 5,
    current_count INTEGER NOT NULL DEFAULT 0,
    window_start TIMESTAMP NOT NULL
);

-- Ledger Events (für schnelle Queries, JSONL bleibt Master)
CREATE TABLE ledger_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP NOT NULL,
    actor TEXT NOT NULL,
    event TEXT NOT NULL,
    job_id TEXT,
    trace_id TEXT,
    zone TEXT,
    artifact_path TEXT,
    meta TEXT  -- JSON
);

CREATE INDEX idx_ledger_timestamp ON ledger_events(timestamp);
CREATE INDEX idx_ledger_job_id ON ledger_events(job_id);
CREATE INDEX idx_ledger_actor ON ledger_events(actor);
```

---

## 2. Kern-Features (Production-Ready)

### 2.1 Idempotenz

```python
# mesh/core/dispatcher.py

async def dispatch_job(job: Job) -> Job:
    """Dispatch job with idempotency guarantee."""
    
    # Check if already executed
    existing = await storage.get_job_by_idempotency_key(job.idempotency_key)
    if existing and existing.status == JobStatus.COMPLETED:
        logger.info(f"Job {job.id} already completed, returning cached result")
        return existing
    
    # Dispatch to broker
    await broker.dispatch(job)
    return job
```

### 2.2 Retry-Logik

```python
# mesh/core/retry_handler.py

async def handle_job_failure(job: Job, error: str):
    """Handle job failure with retry logic."""
    
    if job.retry_count < job.max_retries:
        # Calculate backoff
        if job.retry_backoff == "exponential":
            delay = 2 ** job.retry_count  # 1s, 2s, 4s, 8s
        else:
            delay = job.retry_count + 1   # 1s, 2s, 3s, 4s
        
        # Schedule retry
        job.retry_count += 1
        job.last_retry_at = datetime.utcnow()
        job.status = JobStatus.PENDING
        
        logger.info(f"Retrying job {job.id} in {delay}s (attempt {job.retry_count}/{job.max_retries})")
        
        await asyncio.sleep(delay)
        await dispatcher.dispatch_job(job)
    else:
        # Max retries exceeded
        job.status = JobStatus.FAILED
        job.error = f"Max retries exceeded: {error}"
        await storage.update_job(job)
```

### 2.3 Timeout-Handling

```python
# mesh/offgrid/host/executor.py

async def execute_job(job: Job) -> Dict[str, Any]:
    """Execute job with timeout."""
    
    try:
        async with asyncio.timeout(job.timeout_seconds):
            result = await _run_job_payload(job.payload)
            return result
    except asyncio.TimeoutError:
        raise JobExecutionError(f"Job timed out after {job.timeout_seconds}s")
```

### 2.4 Prioritäts-Queue

```python
# mesh/core/dispatcher.py

async def get_next_job() -> Optional[Job]:
    """Get next job from queue, ordered by priority."""
    
    # Query: ORDER BY priority ASC, created_at ASC
    jobs = await storage.get_pending_jobs_by_priority()
    
    for job in jobs:
        # Check dependencies
        if await all_dependencies_completed(job):
            return job
    
    return None
```

### 2.5 Host-Health-Checks

```python
# mesh/offgrid/host/heartbeat.py

async def heartbeat_loop():
    """Send heartbeat to Core every 10 seconds."""
    
    while True:
        await asyncio.sleep(10)
        
        try:
            await core_api.post("/api/hosts/heartbeat", json={
                "host_id": HOST_ID,
                "status": get_current_status(),
                "current_jobs": get_running_job_ids(),
                "timestamp": datetime.utcnow().isoformat()
            })
        except Exception as e:
            logger.error(f"Heartbeat failed: {e}")


# mesh/core/api/hosts.py

@app.post("/api/hosts/heartbeat")
async def host_heartbeat(data: dict):
    """Receive heartbeat from host."""
    
    host = await storage.get_host(data["host_id"])
    host.last_heartbeat = datetime.utcnow()
    host.status = data["status"]
    host.current_jobs = data["current_jobs"]
    
    await storage.update_host(host)
    return {"ok": True}


# mesh/offgrid/broker/auction_logic.py

async def select_host_for_job(job: Job) -> Optional[Host]:
    """Select best host for job, excluding offline hosts."""
    
    hosts = await core_api.get("/api/hosts")
    
    # Filter: online + not busy + has capabilities
    available = [
        h for h in hosts
        if h.status == HostStatus.ONLINE
        and len(h.current_jobs) < h.max_concurrent
        and all(cap in h.capabilities for cap in job.required_capabilities)
    ]
    
    if not available:
        return None
    
    # Select least loaded
    return min(available, key=lambda h: len(h.current_jobs))
```

### 2.6 Rate-Limiting

```python
# mesh/core/rate_limiter.py

class RateLimiter:
    async def check_limit(self, source: str) -> bool:
        """Check if source is within rate limits."""
        
        config = await storage.get_rate_limit_config(source)
        now = datetime.utcnow()
        
        # Reset window if expired
        if (now - config.window_start).total_seconds() >= 60:
            config.current_count = 0
            config.window_start = now
        
        # Check limits
        if config.current_count >= config.max_jobs_per_minute:
            return False
        
        # Check concurrent
        concurrent = await storage.count_running_jobs_by_source(source)
        if concurrent >= config.max_concurrent_jobs:
            return False
        
        # Increment counter
        config.current_count += 1
        await storage.update_rate_limit_config(config)
        
        return True
```

### 2.7 Job-Dependencies

```python
# mesh/core/dispatcher.py

async def all_dependencies_completed(job: Job) -> bool:
    """Check if all job dependencies are completed."""
    
    if not job.depends_on:
        return True
    
    for dep_id in job.depends_on:
        dep = await storage.get_job(dep_id)
        if not dep or dep.status != JobStatus.COMPLETED:
            return False
    
    return True
```

---

## 3. Migrations-Plan

### Phase 1: Vorbereitung (1-2 Stunden)
- [ ] Backup erstellen (`runtime/` + `v_core/` + `v_mesh/`)
- [ ] Neue Verzeichnisstruktur anlegen (`mesh/`, `external/`)
- [ ] SQLite-Datenbank initialisieren
- [ ] Migrations-Scripts erstellen

### Phase 2: Core-Migration (2-3 Stunden)
- [ ] `v_core/sheratan_core_v2/` → `mesh/core/`
- [ ] Storage auf SQLite umstellen
- [ ] Neue Models implementieren (Job, Host, RateLimitConfig)
- [ ] API-Endpoints anpassen

### Phase 3: Offgrid-Migration (1-2 Stunden)
- [ ] `v_mesh/broker/` → `mesh/offgrid/broker/`
- [ ] `v_mesh/host_daemon/` → `mesh/offgrid/host/`
- [ ] Heartbeat-System implementieren
- [ ] Broker-Logic für Host-Health anpassen

### Phase 4: Runtime-Migration (1 Stunde)
- [ ] `runtime/narrative/` → `mesh/runtime/inbox/`
- [ ] `runtime/input/` → `mesh/runtime/queue/approved/`
- [ ] `runtime/quarantine/` → `mesh/runtime/queue/blocked/`
- [ ] `runtime/output/` → `mesh/runtime/outbox/results/`
- [ ] Ledger-Format beibehalten (`outbox/ledger.jsonl`)

### Phase 5: External-Services (1 Stunde)
- [ ] `v_mini/` → `external/webrelay/`
- [ ] `v_core/sheratan_core_v2/gatekeeper.py` → `external/gatekeeper/`
- [ ] `v_core/sheratan_core_v2/auditor_relay.py` → `external/auditor/`
- [ ] `v_core/sheratan_core_v2/final_decision.py` → `external/final_decision/`

### Phase 6: Production-Features (3-4 Stunden)
- [ ] Idempotenz implementieren
- [ ] Retry-Logic implementieren
- [ ] Timeout-Handling implementieren
- [ ] Prioritäts-Queue implementieren
- [ ] Host-Health-Checks implementieren
- [ ] Rate-Limiting implementieren
- [ ] Job-Dependencies implementieren

### Phase 7: Startup-Scripts (1 Stunde)
- [ ] `START_SHERATAN.ps1` anpassen
- [ ] Neue Pfade konfigurieren
- [ ] Service-Reihenfolge optimieren

### Phase 8: Testing & Verification (2-3 Stunden)
- [ ] End-to-End-Tests
- [ ] Idempotenz-Tests
- [ ] Retry-Tests
- [ ] Timeout-Tests
- [ ] Load-Tests (Rate-Limiting)
- [ ] Dashboard anpassen

### Phase 9: Dokumentation (1-2 Stunden)
- [ ] `docs/ARCHITECTURE.md` erstellen
- [ ] `docs/API.md` aktualisieren
- [ ] `docs/GATES.md` aktualisieren
- [ ] `README.md` aktualisieren

---

## 4. Geschätzte Gesamtdauer

**Minimum:** 13 Stunden  
**Maximum:** 19 Stunden  
**Realistisch:** ~16 Stunden (2 Arbeitstage)

---

## 5. Risiken & Mitigationen

### Risiko 1: Datenverlust während Migration
**Mitigation:** Vollständiges Backup vor Start, schrittweise Migration mit Verifikation

### Risiko 2: Breaking Changes in APIs
**Mitigation:** Alte Endpoints als deprecated markieren, parallel laufen lassen

### Risiko 3: Performance-Probleme mit SQLite
**Mitigation:** Indizes optimieren, bei Bedarf auf PostgreSQL migrieren

### Risiko 4: Komplexität der Retry-Logic
**Mitigation:** Umfangreiche Tests, klare Logging-Strategie

---

## 6. Success-Kriterien

✅ Alle Services starten ohne Fehler  
✅ End-to-End-Job-Execution funktioniert  
✅ Idempotenz: Gleicher Job 2x → gleicher Result  
✅ Retry: Failed Job wird automatisch retried  
✅ Timeout: Lange Jobs werden abgebrochen  
✅ Prioritäten: CRITICAL Jobs werden zuerst ausgeführt  
✅ Health: Tote Hosts werden erkannt  
✅ Rate-Limiting: Überlastung wird verhindert  
✅ Dependencies: Job B wartet auf Job A  
✅ Audit-Trail: Ledger ist vollständig  

---

## 7. Post-Migration

### Sofort nach Migration:
- Monitoring einrichten (Prometheus/Grafana)
- Alerting konfigurieren (tote Hosts, failed jobs)
- Backup-Strategie definieren

### Mittelfristig (1-2 Wochen):
- Load-Testing in Production
- Performance-Optimierungen
- Dashboard-Verbesserungen

### Langfristig (1-3 Monate):
- PostgreSQL-Migration (wenn SQLite zu langsam)
- Distributed Tracing (OpenTelemetry)
- Multi-Tenant-Support

---

## 8. Nächste Schritte

1. **Review dieses Plans** - Feedback einholen
2. **Backup erstellen** - Sicherheit geht vor
3. **Phase 1 starten** - Verzeichnisstruktur anlegen
4. **Iterativ migrieren** - Phase für Phase
5. **Testen, testen, testen** - Keine Kompromisse

---

**Erstellt von:** Antigravity AI  
**Letzte Aktualisierung:** 2026-01-10  
**Status:** Ready for Review
