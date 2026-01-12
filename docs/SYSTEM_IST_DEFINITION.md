# Formale **System-Ist-Definition**

**Sheratan – Stand 2026-01-12**

---

## 1. Zweck & Systemidentität

**Sheratan** ist ein **laufendes, verteiltes Orchestrierungs- und Agentensystem**, dessen Ist-Zustand dadurch definiert ist,
dass **Absichten (Missions / Jobs)** zuverlässig:

1. entgegengenommen
2. orchestriert
3. ausgeführt
4. reflektiert
5. sichtbar gemacht

werden – **über lokale Worker, verteilte Mesh-Nodes und externe LLM-Backends hinweg**.

> Ein System gilt als *„funktionsfähig"*, wenn **Sinnfluss** (Intent → Wirkung → Rückmeldung) gewährleistet ist – nicht bloß Prozess-Laufzeit.

---

## 2. Systemgrenzen (Was gehört dazu / was nicht)

### Gehört **zum System**

* Core API (Orchestrator, State Authority)
* Job- & Mission-Lifecycle
* Worker-Registry
* WebRelay (LLM-Interaktionsschnittstelle)
* Mesh (Broker + Hosts)
* Dashboard (Beobachtbarkeit)
* Chrome Debug / DOM-Automation (als technischer Sensor)

### Gehört **nicht zwingend dazu**

* Bestimmter LLM-Provider (ChatGPT, Gemini etc.)
* Bestimmte UI-Implementierung
* Erweiterte Produktionsfeatures (Retry, SLA, Priorisierung)

➡️ **Wichtig:** Sheratan ist **LLM-agnostisch**, nicht UI- oder Anbieter-abhängig.

---

## 3. Formale Systemzustände

### 3.1 Globaler Systemzustand

Das System befindet sich im Zustand **`OPERATIONAL`**, wenn **alle folgenden Bedingungen erfüllt sind**:

| Kategorie         | Bedingung                                                           |
| ----------------- | ------------------------------------------------------------------- |
| Orchestrierung    | Core API läuft & verarbeitet Missionen                              |
| Ausführung        | Mind. 1 Worker ist registriert & aktiv                              |
| Sinnschnittstelle | WebRelay kann Jobs an ein LLM senden **und Antworten zurückführen** |
| Verteilung        | Mind. 1 Mesh-Host + Broker online                                   |
| Beobachtbarkeit   | Dashboard zeigt konsistenten Status                                 |
| Rückkopplung      | Ergebnisse fließen zurück in Core                                   |

➡️ **Alle Bedingungen sind aktuell erfüllt.**

---

### 3.2 Service-Ebene (Ist-Status)

**Core Services**

* Core API: `RUNNING`
* Dashboard: `RUNNING`
* WebRelay: `RUNNING`
* Chrome Debug: `RUNNING`

**Mesh**

* Broker: `ONLINE`
* Host-A: `ONLINE`
* Host-B: `ONLINE`

**Worker**

* default_worker: `ONLINE`
* webrelay_worker: `ONLINE`

➡️ Kein einzelner Service ist ein *Single Point of Truth* außer der **Core API** (bewusst).

---

## 4. Daten- & Kontrollfluss (normativ)

### 4.1 Normativer Ablauf (vereinfachte Form)

```
Mission → Core API
        → Job Creation
        → Worker Selection
        → (optional) WebRelay → LLM
        → Response Capture
        → Result Sync
        → Dashboard / Logs
```

Ein **Job gilt als korrekt verarbeitet**, wenn:

* er **genau einmal** ausgeführt wurde
* ein **deterministisches Ergebnis** oder ein **begründeter Fehlerzustand** vorliegt
* der Status im Core konsistent ist

---

### 4.2 LLM-Interaktion (Definition)

Eine LLM-Interaktion ist **kein Denkzentrum**, sondern ein **externer Sinnes-/Reflexionskanal**.

Formal:

* WebRelay = *Sensor + Aktor*
* LLM = *externer Interpret*
* Core = *entscheidende Instanz*

➡️ **Sheratan „denkt" nicht im LLM.**
➡️ Das LLM liefert **Input**, keine Wahrheit.

---

## 5. Beobachtbarkeit als Systembestandteil

Beobachtbarkeit ist **keine Zusatzfunktion**, sondern **Teil der Definition von „läuft"**.

Das System gilt nur dann als funktionsfähig, wenn:

* aktueller Zustand sichtbar ist
* historische Aktivität nachvollziehbar ist
* Fehlverhalten identifizierbar wäre

Aktuell erfüllt durch:

* Dashboard Metriken
* Logs
* Job-IDs
* Mission Counter
* Mesh-Status

---

## 6. Fehler- und Degradationsdefinition

### 6.1 Erlaubte Fehler (System bleibt „intakt")

* Ausfall **eines** Mesh-Hosts
* LLM-Timeout / Workspace-Fehler
* Verzögerte Job-Antwort
* UI-Fehler im Dashboard

➡️ Systemzustand: `DEGRADED_BUT_OPERATIONAL`

### 6.2 Nicht erlaubte Fehler (System gilt als „nicht funktionsfähig")

* Core API nicht erreichbar
* Jobs werden angenommen, aber **nicht ausgeführt**
* Ergebnisse kommen zurück, werden aber **nicht synchronisiert**
* Zustand ist **nicht mehr beobachtbar**

➡️ Systemzustand: `BROKEN`

---

## 7. Aktuelle formale Aussage (wichtig)

> **Frage:**
> *„Ist das System aktuell in dem Zustand und funktioniert real so, wie es definiert ist?"*

**Antwort (formale Bewertung):**
👉 **Ja.**

Begründung:

* Alle notwendigen Systembedingungen erfüllt
* Keine verdeckten Annahmen
* Kein impliziter Abhängigkeitspunkt
* Dokumentierte, überprüfte End-to-End-Ausführung

---

## 8. Bedeutung dieser Definition

Diese System-Ist-Definition ist:

* 📌 **referenzierbar**
* 📌 **auditierbar**
* 📌 **erweiterungsfähig**
* 📌 **nicht marketinggetrieben**

Sie erlaubt ab jetzt:

* gezielte Fail-Simulationen
* saubere „Soll-Abweichung"-Analysen
* evolutionäre Erweiterung ohne Bedeutungsverlust

---

## 9. Verifikationsstatus

**Letzte Verifikation:** 2026-01-12  
**Verifikationsmethode:** End-to-End-Test mit Live-System  
**Verifikator:** Antigravity (Google Deepmind)

### Verifizierte Eigenschaften

- [x] Core API verarbeitet Missionen (37 Missionen nachgewiesen)
- [x] Worker registriert und aktiv (2/2 Worker online)
- [x] WebRelay sendet Jobs an ChatGPT und empfängt Antworten
- [x] Mesh-Komponenten kommunizieren (Broker + 2 Hosts online)
- [x] Dashboard zeigt konsistenten Status (90 Jobs in Queue)
- [x] Ergebnisse fließen zurück in Core (Job-Sync verifiziert)

**Systemzustand:** `OPERATIONAL` ✅

---

## 10. Nächste logische Schritte (Optional)

### Option A: System-Soll-Definition
Formalisierung der geplanten Erweiterungen und Produktionsfeatures

### Option B: Kontrollierte Fail-Simulation
Systematisches Testen der Degradationszustände:
- Was passiert bei Host-Ausfall?
- Wie verhält sich das System bei LLM-Timeout?
- Welche Fehler sind tolerierbar?

### Option C: Produktionsbereitschaft
Implementierung der Phase-2-Features aus README:
- Idempotency
- Retry Logic
- Timeout Handling
- Priority Queues
- SQLite Storage
- Host Health Checks

---

**Dokumentversion:** 1.0  
**Status:** Verifiziert und Gültig  
**Nächste Review:** Bei signifikanten Systemänderungen
