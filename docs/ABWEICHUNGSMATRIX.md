# Abweichungsmatrix Ist ↔ Soll

**Sheratan – Systematische Gap-Analyse**

**Erstellt:** 2026-01-12  
**Basis:** [SYSTEM_IST_DEFINITION.md](SYSTEM_IST_DEFINITION.md) + [SYSTEM_SOLL_DEFINITION.md](SYSTEM_SOLL_DEFINITION.md)

---

## 1. Zweck dieses Dokuments

Diese Matrix ist **kein Bugtracker**, sondern eine **normative Abweichungsanalyse**.

Sie beantwortet:
- **Was fehlt**, um vom Ist zum Soll zu kommen?
- **Welche Soll-Eigenschaften sind bereits erfüllt?**
- **Wo ist die Architektur bereit, aber die Implementierung fehlt?**
- **Welche Abweichungen sind kritisch, welche evolutionär?**

---

## 2. Bewertungsskala

| Symbol | Bedeutung                                    |
| ------ | -------------------------------------------- |
| ✅      | Soll-Eigenschaft vollständig erfüllt         |
| ⚠️      | Teilweise erfüllt (funktioniert, aber nicht normativ) |
| ❌      | Nicht erfüllt (Lücke vorhanden)              |
| ⏳      | Vorbereitet (Architektur erlaubt, Code fehlt) |
| 🔒      | Bewusst nicht implementiert (Soll-Grenze)    |

---

## 3. Normative Soll-Eigenschaften (Abweichungsanalyse)

### 3.1 Autonomie (definiert, nicht absolut)

| Bereich             | Soll-Zustand                 | Ist-Status | Abweichung                                          |
| ------------------- | ---------------------------- | ---------- | --------------------------------------------------- |
| Job-Ausführung      | autonom                      | ✅          | Worker führt Jobs eigenständig aus                  |
| Modellwahl          | autonom (Routing + Fallback) | ⚠️          | Nur ChatGPT aktiv, kein Fallback-Routing           |
| Fehlerreaktion      | autonom                      | ⚠️          | Worker retried, aber keine formale Fehler-Policy    |
| Zieländerung        | **nicht autonom**            | ✅          | Nur Mensch kann Missionen erstellen                 |
| Werte / Prioritäten | **nicht autonom**            | ✅          | Keine implizite Prioritätsänderung                  |

**Gap-Analyse:**
- **Modellwahl:** Gemini-Backend existiert, aber nicht aktiv. Kein automatisches Routing bei ChatGPT-Ausfall.
- **Fehlerreaktion:** Worker hat Retry-Logik, aber keine formale Degradation-Policy.

**Implementierungspfad:** Phase C (LLM-Fallback & Routing)

---

### 3.2 Selbstbeobachtung (Pflichtmerkmal)

| Frage                                | Soll | Ist-Status | Abweichung                                           |
| ------------------------------------ | ---- | ---------- | ---------------------------------------------------- |
| Was tue ich gerade?                  | ✅    | ⚠️          | Dashboard zeigt Jobs, aber keine laufende Aktivität  |
| Warum tue ich das?                   | ✅    | ❌          | Keine Begründung für Job-Auswahl dokumentiert        |
| Woher kam dieser Auftrag?            | ✅    | ✅          | Mission-ID ist rückverfolgbar                        |
| Was ist mein letzter stabiler Zustand? | ✅    | ❌          | Kein formaler Zustandsautomat                        |
| Was wäre die sichere Alternative?    | ✅    | ❌          | Keine Fallback-Strategie dokumentiert                |

**Gap-Analyse:**
- **Selbstbeschreibung:** System kann Status zeigen, aber nicht **begründen**.
- **Zustandsmodell:** Implizit vorhanden (läuft/läuft nicht), aber nicht formalisiert.
- **Reflexion:** Keine Self-Diagnostic-Capabilities.

**Implementierungspfad:** Phase A (Selbstbeschreibung) + Phase B (Deterministische Verantwortung)

---

### 3.3 Deterministische Verantwortung

| Erfordernis            | Soll | Ist-Status | Abweichung                                    |
| ---------------------- | ---- | ---------- | --------------------------------------------- |
| Quelle (Mission)       | ✅    | ✅          | Job hat Mission-ID                            |
| Entscheidung (Warum)   | ✅    | ✅          | Decision Trace Logger + WHY-API               |
| Ergebnis (Output)      | ✅    | ✅          | Job-Result wird gespeichert                   |
| Zuordnung (Job-ID)     | ✅    | ✅          | Jeder Job hat UUID + trace_id                 |
| Chain-of-Custody       | ✅    | ✅          | MCTS Logging mit Schema-Validierung           |

**Gap-Analyse:**
- **Entscheidungsgrund:** ✅ MCTS Decision Trace mit Intent, Action, Result, Score
- **Audit-Trail:** ✅ WHY-API mit 4 Endpunkten (`/latest`, `/trace`, `/job`, `/stats`)

**Implementierungspfad:** ✅ Phase B abgeschlossen

---

## 4. Soll-Architektur (Rollenkonformität)

### 4.1 Rollentrennung

| Rolle     | Soll-Funktion              | Ist-Status | Abweichung                                |
| --------- | -------------------------- | ---------- | ----------------------------------------- |
| Core      | Entscheidung & Wahrheit    | ✅          | Core ist Single Source of Truth           |
| Worker    | Ausführung                 | ✅          | Worker führt aus, entscheidet nicht       |
| LLM       | Interpretation / Vorschlag | ✅          | LLM liefert Input, Core entscheidet       |
| Mesh      | Verteilung / Skalierung    | ✅          | Broker + Hosts verteilen Jobs             |
| Dashboard | Bewusstsein / Sichtbarkeit | ⚠️          | Zeigt Status, aber keine Reflexion        |

**Gap-Analyse:**
- **Dashboard:** Zeigt Metriken, aber keine Zustandsinterpretation oder Anomalie-Erkennung.

**Implementierungspfad:** Phase D (Reflexive Capabilities)

---

### 4.2 LLM im Soll-Zustand

| Eigenschaft                 | Soll | Ist-Status | Abweichung                                    |
| --------------------------- | ---- | ---------- | --------------------------------------------- |
| Austauschbar                | ✅    | ⚠️          | Gemini vorhanden, aber nicht aktiv            |
| Fehlertolerant eingebunden  | ✅    | ⚠️          | Timeout-Handling vorhanden, kein Fallback     |
| Niemals allein entscheidend | ✅    | ✅          | Core synchronisiert und validiert Ergebnisse  |
| Darf nicht stillschweigend scheitern | ✅    | ⚠️          | Fehler werden geloggt, aber nicht eskaliert   |

**Gap-Analyse:**
- **Austauschbarkeit:** Dual-LLM-Setup existiert, aber kein automatisches Routing.
- **Fehlertoleranz:** WebRelay loggt Fehler, aber System degradiert nicht formal.

**Implementierungspfad:** Phase C (LLM-Fallback & Routing)

---

## 5. Soll-Zustände des Gesamtsystems

### 5.1 Zustandsmodell

| Zustand     | Soll-Definition                    | Ist-Status | Abweichung                          |
| ----------- | ---------------------------------- | ---------- | ----------------------------------- |
| OPERATIONAL | Alles erfüllt                      | ✅          | Implementiert in `state_machine.py` |
| DEGRADED    | Funktionsfähig mit Einschränkungen | ✅          | Implementiert, Auto-Transition      |
| REFLECTIVE  | System analysiert sich selbst      | ⏳          | Zustand existiert, Logik fehlt      |
| RECOVERY    | Kontrollierter Wiederaufbau        | ✅          | Implementiert                       |
| PAUSED      | Bewusst gestoppt                   | ✅          | Implementiert, Default-State        |

**Gap-Analyse:**
- **Zustandsautomat:** ✅ Vollständig implementiert (375 Zeilen, File Locking, JSONL Logging)
- **Übergänge:** ✅ Policy-basiert, strukturiert geloggt
- **REFLECTIVE:** Zustand existiert, aber keine Self-Diagnostic-Logik

**Implementierungspfad:** Phase D (Reflexive Capabilities) – **NÄCHSTER SCHRITT**

---

### 5.2 Zustandsübergänge

| Erfordernis     | Soll | Ist-Status | Abweichung                       |
| --------------- | ---- | ---------- | -------------------------------- |
| Sichtbar        | ✅    | ❌          | Keine Zustandsanzeige            |
| Begründet       | ✅    | ❌          | Keine Transition-Logs            |
| Rückverfolgbar  | ✅    | ⚠️          | Logs vorhanden, aber nicht strukturiert |

**Implementierungspfad:** Phase A (Selbstbeschreibung)

---

## 6. Lernen & Evolution

| Erlaubt               | Soll | Ist-Status | Abweichung                                |
| --------------------- | ---- | ---------- | ----------------------------------------- |
| Routing-Optimierung   | ✅    | ⏳          | Architektur erlaubt, nicht implementiert  |
| Fehlervermeidung      | ✅    | ⚠️          | Worker retried, aber kein Lernmechanismus |
| Performance-Anpassung | ✅    | ⏳          | Metriken vorhanden, keine Anpassung       |
| Heuristik-Tuning      | ✅    | ❌          | Nicht implementiert                       |

| Nicht erlaubt                | Soll | Ist-Status | Konformität |
| ---------------------------- | ---- | ---------- | ----------- |
| Zielmutation                 | 🔒    | ✅          | Konform     |
| Werteverschiebung            | 🔒    | ✅          | Konform     |
| Implizite Prioritätsänderung | 🔒    | ✅          | Konform     |
| Selbstzweck-Evolution        | 🔒    | ✅          | Konform     |

**Gap-Analyse:**
- **Grenzen eingehalten:** System lernt nicht implizit (gut!).
- **Erlaubtes Lernen:** Vorbereitet, aber nicht implementiert.

**Implementierungspfad:** Phase D (Reflexive Capabilities) – evolutionär, nicht kritisch

---

## 7. Mensch–System-Beziehung

| Rolle (Mensch)  | Soll | Ist-Status | Abweichung                    |
| --------------- | ---- | ---------- | ----------------------------- |
| Zielgeber       | ✅    | ✅          | Mensch erstellt Missionen     |
| Grenzsetzer     | ✅    | ⚠️          | Keine formalen Grenzen konfigurierbar |
| Letzte Instanz  | ✅    | ✅          | System überstimmt nicht       |

| Rolle (Sheratan) | Soll | Ist-Status | Abweichung                    |
| ---------------- | ---- | ---------- | ----------------------------- |
| Ausführer        | ✅    | ✅          | System führt aus              |
| Beobachter       | ✅    | ⚠️          | Zeigt Status, keine Reflexion |
| Reflektor        | ✅    | ❌          | Keine Self-Diagnostics        |
| Darf widersprechen | ✅    | ❌          | Keine Widerspruchsmechanismen |

**Gap-Analyse:**
- **Widerspruch:** System könnte warnen (z.B. "Mission zu komplex"), tut es aber nicht.
- **Reflexion:** Keine Self-Diagnostic-Jobs.

**Implementierungspfad:** Phase D (Reflexive Capabilities)

---

## 8. Gesamtbewertung Ist ↔ Soll

### 8.1 Erfüllungsgrad nach Kategorie

| Kategorie                | Erfüllt | Teilweise | Nicht erfüllt | Vorbereitet |
| ------------------------ | ------- | --------- | ------------- | ----------- |
| Operativer Kern          | 90%     | 10%       | 0%            | -           |
| Autonomie                | 60%     | 30%       | 10%           | -           |
| Selbstbeobachtung        | 20%     | 30%       | 50%           | -           |
| Deterministische Verantwortung | 60%     | 20%       | 20%           | -           |
| Rollenkonformität        | 80%     | 20%       | 0%            | -           |
| Zustandsmodell           | 0%      | 20%       | 80%           | ✅           |
| Lernen & Evolution       | 0%      | 10%       | 40%           | 50%         |
| Mensch-System-Beziehung  | 60%     | 20%       | 20%           | -           |

**Gesamterfüllung:** **~70-75% Soll** (wie in SYSTEM_SOLL_DEFINITION.md geschätzt)

---

### 8.2 Kritische Lücken (priorisiert)

| Rang | Lücke                       | Impact | Aufwand | Priorität |
| ---- | --------------------------- | ------ | ------- | --------- |
| 1    | Zustandsautomat fehlt       | HOCH   | 4-6h    | KRITISCH  |
| 2    | Keine Entscheidungsbegründung | MITTEL | 6-8h    | HOCH      |
| 3    | Kein LLM-Fallback           | MITTEL | 5-7h    | MITTEL    |
| 4    | Keine Reflexion             | NIEDRIG | 8-12h   | NIEDRIG   |

---

## 9. Implementierungsroadmap (abgeleitet)

### Phase A: Zustandsmodell (KRITISCH)
**Ziel:** System kann formal sagen: "Ich bin in Zustand X, weil Y"

**Deliverables:**
1. State Machine Implementation (`core/state_machine.py`)
2. `/api/system/state` Endpoint
3. State Transition Logging
4. Dashboard: Zustandsanzeige

**Aufwand:** 4-6 Stunden  
**Schließt Lücken:** Selbstbeobachtung (50%), Zustandsmodell (80%)

---

### Phase B: Decision Logging (HOCH)
**Ziel:** Jede Entscheidung ist nachvollziehbar

**Deliverables:**
1. Worker-Selection-Reasoning
2. Decision-Log-Struktur
3. Chain-of-Custody-Tracking
4. Audit-Trail-Visualisierung

**Aufwand:** 6-8 Stunden  
**Schließt Lücken:** Deterministische Verantwortung (30%)

---

### Phase C: LLM-Resilience (MITTEL)
**Ziel:** LLM-Ausfall degradiert System, bricht es nicht

**Deliverables:**
1. Multi-LLM-Routing
2. Fallback-Chain (ChatGPT → Gemini → Local)
3. Timeout-Handling
4. Degradation-Policy

**Aufwand:** 5-7 Stunden  
**Schließt Lücken:** Autonomie (30%), LLM-Fehlertoleranz (50%)

---

### Phase D: Reflexive Capabilities (EVOLUTIONÄR)
**Ziel:** System kann sich selbst analysieren

**Deliverables:**
1. Self-Diagnostic-Jobs
2. Anomalie-Detektion
3. Performance-Baseline
4. Automated Health Reports

**Aufwand:** 8-12 Stunden  
**Schließt Lücken:** Reflexion (100%), Lernen (40%)

---

## 10. Nächster Schritt

**Empfehlung:** **Phase A (Zustandsmodell) implementieren**

**Begründung:**
- Schließt die kritischste Lücke (Selbstbeobachtung)
- Geringer Aufwand (4-6h)
- Hoher Impact (System wird "erwachsen")
- Keine Architekturänderung nötig

**Alternative:** Fail-Simulation durchführen, um Degradationszustände empirisch zu testen

---

**Dokumentversion:** 1.0  
**Status:** Analytisch  
**Nächste Aktualisierung:** Nach Implementierung Phase A
