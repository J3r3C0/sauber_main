# Sheratan - Aktuelle Aufgaben

**Stand**: 2026-01-14

---

## ✅ Erledigt (Heute)

- [x] Crypto Session auf v0.16-alpha upgraded (Replay-Schutz, Session-IDs)
- [x] Migration TODOs verifiziert (keine Breaking Changes)
- [x] Dokumentation konsolidiert (README.md, QUICKSTART.md)
- [x] system_overview.md erstellt (Ports, APIs, Commands)

---

## 🎯 Priorität 1 - Stabilität

### System-Verifikation
- [ ] Alle 8 Services testen (Health Checks)
- [ ] Job-Flow durchlaufen (Mission → Task → Job → Result)
- [ ] State Machine Transitions testen
- [ ] Logs auf Fehler prüfen

### Dokumentation
- [x] README.md aktualisiert
- [x] QUICKSTART.md aktualisiert
- [ ] Veraltete Docs archivieren (`docs/archive/`)

---

## 🔬 Priorität 2 - Testing

### Crypto Sessions (Optional)
- [ ] Handshake zwischen Host-A und Host-B testen
- [ ] Encrypted Session erstellen
- [ ] Replay-Schutz verifizieren

### Performance
- [ ] Baseline-Metriken sammeln
- [ ] Anomaly Detection beobachten
- [ ] Dispatcher-Performance messen

---

## 🚀 Priorität 3 - Features

### Mesh Encryption (Experimentell)
- [ ] `--noise 1` Flag aktivieren (wenn gewünscht)
- [ ] Encrypted Sessions im Live-Mesh testen
- [ ] Performance-Impact messen

### Monitoring
- [ ] WHY-API nutzen für Decision Analysis
- [ ] Decision Traces visualisieren
- [ ] Performance-Dashboards erstellen

---

## 📋 Backlog

- [ ] Burn-In Tests durchführen (siehe `docs/PHASE1_BURN_IN_TEST_PLAN.md`)
- [ ] Multi-Node Setup testen
- [ ] Production-Deployment vorbereiten
- [ ] Phase 2 Features evaluieren (siehe `docs/PHASE2_DECISION_MATRIX.md`)

---

## 🚨 Bekannte Issues

- ⚠️ Crypto Sessions vorbereitet, aber nicht im Live-Mesh getestet
- ⚠️ Einige Docs in `docs/` sind veraltet (vor 2026-01-14)

---

## 📝 Notizen

**Nächste Session:**
1. System-Health-Check durchführen
2. Veraltete Docs archivieren
3. Entscheiden: Crypto-Sessions aktivieren oder nicht?

**Langfristig:**
- Monitoring verbessern
- Performance optimieren
- Production-Readiness erhöhen
