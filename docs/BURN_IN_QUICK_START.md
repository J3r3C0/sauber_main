# Burn-In Test Quick Start Guide

## ⚠️ WICHTIG: System muss laufen!

Die Burn-In Tests erfordern ein **laufendes Sheratan-System**.

---

## Schnellstart

### 1. System starten
```powershell
cd C:\sauber_main
.\START_COMPLETE_SYSTEM.bat
```

**Warte 30 Sekunden** bis alle Services hochgefahren sind.

### 2. Verify System läuft
```powershell
# Core API Check
Invoke-WebRequest -Uri "http://localhost:8001/health" -UseBasicParsing

# Sollte 200 OK zurückgeben
```

### 3. Burn-In Tests ausführen
```powershell
.\scripts\RUN_ALL_BURN_IN_TESTS.ps1
```

---

## Fehlerbehandlung

### "Connection refused" / "400 Bad Request"
**Problem**: System läuft nicht

**Lösung**:
```powershell
# System starten
.\START_COMPLETE_SYSTEM.bat

# 30 Sekunden warten
Start-Sleep -Seconds 30

# Erneut versuchen
.\scripts\RUN_ALL_BURN_IN_TESTS.ps1
```

### "Property 'status' cannot be found"
**Problem**: Script-Bug (wurde gefixt)

**Lösung**: 
```powershell
# Neueste Version pullen
git pull

# Erneut versuchen
.\scripts\RUN_ALL_BURN_IN_TESTS.ps1
```

---

## Ergebnisse

### Report-Location:
```
runtime/tests/FINAL_REPORT.json
```

### Anzeigen:
```powershell
Get-Content runtime/tests/FINAL_REPORT.json | ConvertFrom-Json | Format-List
```

### Test-Logs:
```
runtime/tests/test_*/stdout.log
```

---

## PC2 Workflow

### Auf PC2:
```powershell
# 1. System starten
cd C:\sheratan_test
.\START_COMPLETE_SYSTEM.bat

# 2. Warten
Start-Sleep -Seconds 30

# 3. Tests ausführen
.\scripts\RUN_ALL_BURN_IN_TESTS.ps1
```

### Von PC1 monitoren:
```
Dashboard: http://192.168.1.XXX:3001
WHY-API:   http://192.168.1.XXX:8001/api/why/stats
```

---

## Test-Übersicht

| Test | Priorität | Dauer | Zweck |
|------|-----------|-------|-------|
| `test_p0_state_display` | P0 | ~5s | Preconditions: System läuft |
| `test_p1_worker_kill` | P1 | ~30s | Worker Crash Recovery |
| `test_p1_core_kill` | P1 | ~30s | Core Crash Recovery |
| `test_p1_power_loss` | P1 | ~30s | Power Loss Simulation |
| `test_p2_lock_stress` | P2 | ~60s | Lock Contention |
| `test_p3_partial_write` | P3 | ~30s | Partial Write Recovery |
| `test_p3_watchdog_spam` | P3 | ~30s | Watchdog Stress |

**Gesamt**: ~3-5 Minuten

---

## Exit Codes

- `0` = Alle Tests bestanden
- `1` = Mindestens ein Test fehlgeschlagen
- `2` = P0 (Preconditions) fehlgeschlagen

---

**TL;DR**:
```powershell
.\START_COMPLETE_SYSTEM.bat
Start-Sleep -Seconds 30
.\scripts\RUN_ALL_BURN_IN_TESTS.ps1
```
