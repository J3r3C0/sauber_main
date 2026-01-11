# Sheratan Quick Start Guide (Windows)

## Dry-Run Mode (Lernen & Beobachten)

### 1. System starten
```bash
START_DRYRUN.bat
```

Das startet:
- **Core API** auf Port 8001 (Missions, Tasks, Jobs)
- **Journal Sync API** auf Port 8100 (für Replicas)
- **Governance**: DRY-RUN (Margins werden nur geloggt, nicht angewendet)

### 2. Test-Job senden

**Option A: Über API**
```bash
curl -X POST http://localhost:8001/api/missions/quickstart ^
  -H "Content-Type: application/json" ^
  -d "{\"user_id\":\"test_user\",\"goal\":\"Test Settlement Flow\"}"
```

**Option B: Über mobile_cli.py**
```bash
python mobile_cli.py
# Dann: "create mission" -> "add task" -> "dispatch"
```

### 3. Logs beobachten

Im **Sheratan Core** Terminal siehst du:
```
[DRY-RUN] Settlement for job_abc123: margin=0.1500, provider_share=8.5000
[bridge] 💰 Settled job abc123: 10.0 TOK (margin: 15.0%)
```

**Wichtig**: Im Dry-Run werden **keine echten Balances geändert**, nur geloggt!

### 4. Reconciliation prüfen

Nach 10-20 Jobs:
```bash
python -m mesh.registry.reconciliation_report ledger_events.jsonl
```

Zeigt:
- Total User Costs
- Total Payouts
- Operator Revenue
- Avg. Margin

### 5. Worker Stats checken

```bash
curl http://localhost:8001/api/mesh/workers | python -m json.tool
```

Zeigt für jeden Worker:
- `success_ema` (Erfolgsrate)
- `latency_ms_ema` (Durchschnittliche Latenz)
- `consecutive_failures` (Fehler-Counter)
- `is_offline` (Cooldown-Status)

---

## Production Mode (Scharf schalten)

### Wann umschalten?
Nach **50+ Jobs** im Dry-Run ohne Anomalien:
- Margins sehen plausibel aus (12-20%)
- Keine unerwarteten Cooldowns
- Reconciliation stimmt

### Umschalten
```bash
# 1. System stoppen
STOP_SHERATAN.bat

# 2. Production starten
START_PRODUCTION.bat
```

**Unterschied**: `GOV_DRY_RUN=0` → Settlements ändern jetzt **echte Balances**!

---

## Monitoring Commands

### Operator Revenue
```bash
python -m mesh.registry.reconciliation_report ledger_events.jsonl
```

### Journal Integrity
```bash
python -m core.journal_cli verify ledger_events.jsonl
```

### Worker Health
```bash
curl http://localhost:8001/api/mesh/workers
```

### Ledger Balance
```bash
curl http://localhost:8001/api/mesh/ledger/test_user
```

---

## Troubleshooting

### "Port already in use"
```bash
STOP_SHERATAN.bat
# Warte 5 Sekunden, dann neu starten
```

### "No workers available"
Worker muss sich erst registrieren. Check:
```bash
curl http://localhost:8001/api/mesh/workers
```

Wenn leer → Worker-Prozess starten oder manuell registrieren.

### "Settlement failed (insufficient balance)"
User hat nicht genug Guthaben:
```bash
# Credit user
curl -X POST http://localhost:8001/api/mesh/ledger/test_user/credit ^
  -H "Content-Type: application/json" ^
  -d "{\"amount\":1000}"
```

---

## Next Steps

1. **Woche 1**: Dry-Run mit 50+ Jobs
2. **Woche 2**: Production mit echtem Traffic
3. **Woche 3**: Margin-Tuning basierend auf echten Daten
4. **Monat 2**: Replica-Node für Monitoring starten
