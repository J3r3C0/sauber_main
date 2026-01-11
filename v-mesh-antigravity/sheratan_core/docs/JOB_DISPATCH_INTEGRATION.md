# Job Dispatch Integration: Core ↔ Offgrid

## Übersicht

Die Job Dispatch Integration ermöglicht es Core-Star, Jobs an Offgrid-Hosts zu delegieren.
Der Offgrid-Broker führt eine Mikro-Auktion durch, um den besten Host zu finden.

## Architektur

```
Core (webrelay_bridge)
    ↓ HTTPS POST
Offgrid Broker (auction_api)
    ↓ Micro-Auction
Winning Host (daemon_stub)
    ↓ Execute + Receipt
    ↑ Result
Core (Job Updated)
```

## Komponenten

### 1. Core-Seite

**`schema_mapping.py`**
- Konvertiert Core-Job → Offgrid-Job
- Konvertiert Offgrid-Result → Core-Result
- Schätzt Compute-Size (tokens) aus Payload

**`offgrid_bridge.py`**
- HTTP-Client für Broker-Kommunikation
- HMAC-SHA256-Authentifizierung
- Retry-Logic (3x, exponential backoff)
- Error-Handling (BrokerUnavailable, NoHostsAvailable, JobTimeout)

**`webrelay_bridge.py` (modified)**
- Hybrid-Dispatch-Mode:
  - `auto`: Versucht Offgrid, Fallback zu lokal
  - `offgrid`: Nur Offgrid (fail wenn unavailable)
  - `disabled`: Nur lokale File-Queue
- Backward-Compatible

### 2. Offgrid-Seite

**`broker/auction_api.py`**
- HTTP-Server (Port 9000)
- Endpunkte:
  - `POST /auction` → Job annehmen, Auktion laufen lassen
  - `GET /status` → Health-Check
- Verwendet existing `broker_stub.py` Logic
- HMAC-Signature-Verification

## Konfiguration

### Environment Variables (Core)

```bash
# Offgrid Mode
OFFGRID_MODE=auto              # auto | offgrid | disabled
OFFGRID_BROKER_URL=http://127.0.0.1:9000
OFFGRID_AUTH_KEY=shared-secret
```

### Modes

| Mode | Verhalten |
|------|-----------|
| `auto` | Versucht Offgrid, Fallback zu lokal wenn unavailable |
| `offgrid` | Nur Offgrid (wirft Error wenn Broker down) |
| `disabled` | Nur lokale File-Queue (wie bisher) |

## Verwendung

### 1. Offgrid-Infrastruktur starten

```bash
# Terminal 1: Host-A
cd offgrid-net-v0.16.4-with-memory-PRO-UI-POLICY-ROTATE
python host_daemon/daemon_stub.py --port 8081 --node_id node-A

# Terminal 2: Host-B
python host_daemon/daemon_stub.py --port 8082 --node_id node-B

# Terminal 3: Broker Auction API
python broker/auction_api.py --port 9000
```

### 2. Core mit Offgrid starten

```bash
cd core

# Set Environment
export OFFGRID_MODE=auto
export OFFGRID_BROKER_URL=http://127.0.0.1:9000
export OFFGRID_AUTH_KEY=shared-secret

# Start Core
python -m uvicorn sheratan_core_v2.main:app --host 0.0.0.0 --port 8001
```

### 3. Job dispatchen

```bash
# Create Mission
curl -X POST http://localhost:8001/api/missions \
  -H "Content-Type: application/json" \
  -d '{"title": "Test Offgrid", "description": "Test"}'

# Create Task
curl -X POST http://localhost:8001/api/missions/{mission_id}/tasks \
  -d '{"name": "llm_call", "kind": "llm_call"}'

# Create Job
curl -X POST http://localhost:8001/api/tasks/{task_id}/jobs \
  -d '{"payload": {"prompt": "Test"}}'

# Dispatch → Geht automatisch zu Offgrid (wenn Mode=auto/offgrid)
curl -X POST http://localhost:8001/api/jobs/{job_id}/dispatch
```

### 4. Verify

```bash
# Check Job Status
curl http://localhost:8001/api/jobs/{job_id}

# Job result sollte enthalten:
{
  "status": "completed",
  "result": {
    "ok": true,
    "offgrid_receipt": {
      "node_id": "node-A",
      "metrics": {"compute_tokens_m": 0.1, "latency_ms": 1234}
    },
    "host": "http://127.0.0.1:8081"
  }
}
```

## Testing

### Automatisierter Test

```bash
cd 2_sheratan_core
python test_offgrid_integration.py
```

### Manueller Test

1. **Start Services** (see above)
2. **Dispatch Job** via Core API
3. **Check Logs:**
   - Core: `[offgrid_bridge] Dispatching job...`
   - Broker: `[auction_api] Running auction for job...`
   - Host: `[host-daemon] POST /run...`
4. **Verify Receipt** in job result

## Sicherheit

### Phase 1: HMAC-SHA256

- Shared-Secret zwischen Core und Broker
- Signatur über gesamten Payload
- Timestamp-Check (5min window gegen Replay)

**Payload-Format:**

```json
{
  "job_id": "job-123",
  "type": "compute",
  "size": 0.25,
  "timestamp": 1704278400,
  "signature": "abc123..."
}
```

### Phase 2 (TODO): Ed25519

- Core signiert Jobs mit Private Key
- Broker verifiziert mit Core's Public Key
- Host signiert Receipts

## Error-Handling

### Broker Unavailable

```
Mode=auto    → Fallback zu lokal
Mode=offgrid → Raise BrokerUnavailable
```

### No Hosts Available

```
Retries: 3x mit 2s/4s/8s Delay
Danach: Raise NoHostsAvailable
```

### Job Timeout

```
Timeout: 30s (konfigurierbar)
Wenn überschritten: Raise JobTimeout
```

## Monitoring

### Logs

**Core:**
```
[webrelay_bridge] Offgrid Broker available at http://127.0.0.1:9000
[webrelay_bridge] Dispatching job job-123 via Offgrid
[offgrid_bridge] Auction successful: host=http://127.0.0.1:8081, quote=0.03
[webrelay_bridge] Offgrid dispatch successful: completed
```

**Broker:**
```
[auction_api] Running auction for job job-123
[auction_api] Trying host http://127.0.0.1:8081 (quote=0.03)
```

**Host:**
```
[host-daemon] POST /run job-123
```

### Metrics

- Jobs dispatched: `offgrid_jobs_total`
- Job latency: `offgrid_job_duration_seconds`
- Broker errors: `offgrid_broker_errors_total`

## Troubleshooting

### "Offgrid Broker not available"

- Check Broker is running: `curl http://127.0.0.1:9000/status`
- Check `OFFGRID_BROKER_URL` is correct
- Check network/firewall

### "No hosts available"

- Check Hosts are running: `curl http://127.0.0.1:8081/announce`
- Check Discovery: `cat discovery/mesh_hosts.json`
- Check Host `/toggle` is `true`

### "Invalid signature"

- Check `OFFGRID_AUTH_KEY` matches on Core and Broker
- Check timestamps are in sync (NTP)

## Performance

### Latency

- Local File-Queue: ~50ms
- Offgrid (UDP, local): ~100-200ms
- Offgrid (LoRa): ~1-5s

### Throughput

- Broker: ~100 jobs/s
- Host: ~10 jobs/s (depends on job type)
- Limiting factor: LLM inference time

## Roadmap

- [x] M1: Foundation (Schema Mapping, API Specs)
- [x] M2: Job Dispatch (Offgrid Bridge, Auction API, Hybrid Mode)
- [ ] M3: Failover Logic (Quorum, Reassignment)
- [ ] M4: Ed25519-Signaturen
- [ ] M5: Off-Grid-Transport (LoRa, BLE)
- [ ] M6: Production Hardening (Rate-Limiting, Monitoring)

---

**Version:** 1.0  
**Status:** ✅ Implemented  
**Datum:** 2026-01-03
