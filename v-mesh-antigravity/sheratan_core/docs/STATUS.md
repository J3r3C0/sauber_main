# Sheratan Offgrid Integration - Status & Next Steps

## ✅ Was wurde implementiert

### 1. Core → Offgrid Job Dispatch
- **Schema Mapping** (`core/sheratan_core_v2/schema_mapping.py`): Konvertiert Core-Jobs zu Offgrid-Format
- **Offgrid Bridge** (`core/sheratan_core_v2/offgrid_bridge.py`): HTTP-Client für Broker-Kommunikation
- **Hybrid Dispatch** (`core/sheratan_core_v2/webrelay_bridge.py`): Versucht Offgrid, fällt zurück auf lokale Queue
- **HMAC Auth**: Shared-Secret Authentifizierung zwischen Core und Broker

### 2. Offgrid Broker API
- **Auction API** (`broker/auction_api.py`): HTTP-Server für Job-Auktionen
- **Discovery**: Lädt Hosts aus `discovery/mesh_hosts.json` (mit Fallback zu localhost)
- **Endpoints**: `POST /auction`, `GET /status`

### 3. Configuration
- **ENV-Variablen** (`.env` in `core/`):
  ```
  OFFGRID_MODE=auto          # auto | offgrid | disabled
  OFFGRID_BROKER_URL=http://127.0.0.1:9000
  OFFGRID_AUTH_KEY=shared-secret
  ```

### 4. Scripts
- `START_SHERATAN.ps1`: Startet alle 4 Services (2 Hosts, Broker, Core)
- `STOP_SHERATAN.ps1`: Stoppt alle Services sauber
- `simple_test.ps1`: End-to-End Test
- `MANUAL_TEST.ps1`: Anleitung für manuellen Test

## ⚠ Aktuelles Problem

**Offgrid wird nicht verwendet** - Jobs gehen in `file_queue` statt `offgrid`.

### Mögliche Ursachen:
1. **Core startet nicht richtig** im START_SHERATAN.ps1 Script
2. **offgrid_bridge** wird nicht initialisiert
3. **ENV-Variablen** werden nicht geladen

### Debug-Logs hinzugefügt:
In `webrelay_bridge.py` zeigen jetzt beim Dispatch:
```
[webrelay_bridge] === DISPATCH for <job_id> ===
[webrelay_bridge]   offgrid_bridge: True/False
[webrelay_bridge]   offgrid_mode: 'auto'/'disabled'
[webrelay_bridge]   should_try_offgrid: True/False
```

## 🔧 Nächste Schritte

### 1. Manual Test durchführen
```powershell
# Siehe MANUAL_TEST.ps1 für Details
# Starte 4 Terminals manuell:
# - Terminal 1: Host-A (Port 8081)
# - Terminal 2: Host-B (Port 8082)
# - Terminal 3: Broker (Port 9000)
# - Terminal 4: Core (Port 8001)

# Dann teste:
.\simple_test.ps1
```

### 2. Core-Logs prüfen
Schaue in Terminal 4 (Core) nach:
- Wird `.env` geladen?
- Wird `OffgridBridge` initialisiert?
- Was zeigen die `=== DISPATCH ===` Debug-Logs?

### 3. Wenn Offgrid funktioniert
Du solltest sehen:
```
✓ Dispatched via: offgrid
  Status: completed
```

Statt:
```
✓ Dispatched via: file_queue
  File: C:\...\webrelay_out\<job_id>.job.json
```

### 4. Broker-Logs prüfen
In Terminal 3 (Broker) solltest du sehen:
```
[auction_api] Looking for discovery at: ...
[auction_api] ✓ Found 2 hosts from discovery: [...]
[auction_api] Running auction for job ...
```

## 📝 Wichtige Dateien

| Datei | Zweck |
|-------|-------|
| `core/.env` | Offgrid-Konfiguration |
| `core/sheratan_core_v2/webrelay_bridge.py` | Dispatch-Logik |
| `core/sheratan_core_v2/offgrid_bridge.py` | Broker-Client |
| `broker/auction_api.py` | Broker-Server |
| `discovery/mesh_hosts.json` | Host-Registry |

## 🎯 Erfolgs-Kriterien

- [ ] Core startet ohne Fehler
- [ ] `.env` wird geladen
- [ ] `OffgridBridge` wird initialisiert
- [ ] `should_try_offgrid = True`
- [ ] Broker empfängt Auction-Request
- [ ] Broker findet Hosts
- [ ] Job wird dispatched
- [ ] `simple_test.ps1` zeigt `offgrid` statt `file_queue`
- [ ] Job-Status ist `completed`

## 💡 Troubleshooting

### Core startet nicht
- Prüfe ob Port 8001 frei ist: `.\STOP_SHERATAN.ps1`
- Starte manuell: `cd core; python -m uvicorn sheratan_core_v2.main:app --host 0.0.0.0 --port 8001`
- Schaue nach Import-Fehlern

### Offgrid wird nicht verwendet
- Prüfe Core-Logs für `=== DISPATCH ===`
- Stelle sicher dass `.env` existiert in `core/`
- Prüfe `offgrid_bridge: True` in Logs

### Broker findet keine Hosts
- Prüfe `discovery/mesh_hosts.json` existiert
- Broker sollte Fallback zu localhost verwenden
- Schaue Broker-Logs für `Using hosts: [...]`

## 🚀 Nächste Integration-Punkte (nach Job Dispatch)

1. **Storage Backend → Offgrid EC/Replication**
2. **LCP-Kosten → Offgrid Ledger**
