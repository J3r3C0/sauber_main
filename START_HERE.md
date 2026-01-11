# SHERATAN CLEAN BUILD - START HERE

**Datum:** 2026-01-10  
**Status:** Bereit für Clean Build

---

## 🎯 DEIN AUFTRAG (für neuen Chat)

**Sage im ersten Prompt:**

> "Lies diese Datei (`C:\sauber_main\START_HERE.md`) und die Checkliste (`clean_build_checklist.md` in Artifacts). Baue ein sauberes Sheratan-System in `C:\sauber_main\` mit nur funktionierenden Komponenten aus `C:\projectroot` und `C:\Sheratan\sheratan`."

---

## 📚 Wichtige Dokumente (in Artifacts)

1. **`clean_build_checklist.md`** - Was rein soll, was nicht
2. **`SHERATAN_REFACTORING_PLAN.md`** - Production-Features (TODO)
3. **`MIGRATION_MAP.md`** - Was woher wohin verschoben wurde
4. **`task.md`** - Refactoring-Fortschritt

---

## 🗂️ Quell-Systeme

### C:\projectroot (Refactored Mesh)
- ✅ Broker (Port 9000)
- ✅ Hosts (Port 8081, 8082)
- ✅ Gates (G0-G4)
- ✅ Gatekeeper, Auditor, Final Decision
- ✅ WebRelay (Port 3001 → ändern zu 3000)
- ✅ Runtime-Zonen (4→3 vereinfacht)

### C:\Sheratan\sheratan (Dashboard System)
- ✅ React Dashboard (Port 3001)
- ✅ Core API (Port 8001)
- ✅ Worker Loop
- ⚠️ Evtl. bessere LCP Actions

---

## 🎯 Ziel-Struktur

```
C:\sauber_main\
├── mesh/              # Mesh-intern
│   ├── core/
│   ├── offgrid/
│   └── runtime/
├── external/          # Mesh-extern
│   ├── webrelay/
│   ├── gatekeeper/
│   ├── auditor/
│   └── final_decision/
├── dashboard/         # React UI
├── tools/             # Utilities
├── config/            # .env
├── docs/              # Doku
└── START.ps1          # Master startup
```

---

## ⚙️ Ports (Final)

| Service | Port |
|---------|------|
| Core API | 8001 |
| WebRelay | 3000 |
| Broker | 9000 |
| Host-A | 8081 |
| Host-B | 8082 |
| Dashboard | 3001 |
| Chrome Debug | 9222 |

---

## ✅ Success Criteria

- [ ] Alle Services starten ohne Fehler
- [ ] Dashboard zeigt 2 Hosts online
- [ ] Job-Submission funktioniert (inbox → execution → outbox)
- [ ] Gates funktionieren (G0-G4)
- [ ] Audit-Pipeline funktioniert
- [ ] Ledger schreibt Events
- [ ] Keine Port-Konflikte
- [ ] Keine Unicode-Fehler
- [ ] Saubere Terminal-Ausgabe

---

## 🚀 Nächste Schritte

1. Neuen Chat starten
2. Diese Datei erwähnen
3. Clean Build ausführen (~1-2 Stunden)
4. Testen
5. Production-Features hinzufügen (siehe TODO.md-Marker)

---

**Geschätzte Zeit:** 1-2 Stunden  
**Token-Budget:** ~90.000 verbleibend  
**Bereit:** JA ✅
