# **System-Soll-Definition**

**Sheratan – Zielzustand (normativ, evolutionär)**

---

## 1. Grundsatz (oberste Norm)

**Sheratan soll ein selbstkonsistentes, überprüfbares und evolutionäres Handlungssystem sein**,
das **Intent → Entscheidung → Ausführung → Reflexion → Anpassung**
als **geschlossenen Kreislauf** betreibt – **ohne Abhängigkeit von einzelnen Tools, Modellen oder UIs**.

> Ein System erfüllt den Soll-Zustand **nicht**, wenn es nur funktioniert.
> Es erfüllt ihn erst, wenn es **seinen eigenen Zustand beurteilen kann**.

---

## 2. Zielidentität des Systems

Sheratan **soll**:

1. **nicht nur Jobs ausführen**, sondern deren *Sinn* kennen
2. **nicht nur reagieren**, sondern *begründet handeln*
3. **nicht nur stabil laufen**, sondern *bewusst degradieren*
4. **nicht nur wachsen**, sondern *gerichtet lernen*

➡️ Sheratan ist **kein Tool**, sondern ein **operatives Meta-System**.

---

## 3. Normative Soll-Eigenschaften (verbindlich)

### 3.1 Autonomie (definiert, nicht absolut)

Sheratan **soll autonom sein**, **innerhalb expliziter Grenzen**:

| Bereich             | Soll-Zustand                 |
| ------------------- | ---------------------------- |
| Job-Ausführung      | autonom                      |
| Modellwahl          | autonom (Routing + Fallback) |
| Fehlerreaktion      | autonom                      |
| Zieländerung        | **nicht autonom**            |
| Werte / Prioritäten | **nicht autonom**            |

➡️ Autonomie ist **funktional**, nicht moralisch.

---

### 3.2 Selbstbeobachtung (Pflichtmerkmal)

Sheratan **muss jederzeit sagen können**:

* Was tue ich gerade?
* Warum tue ich das?
* Woher kam dieser Auftrag?
* Was ist mein letzter stabiler Zustand?
* Was wäre die sichere Alternative?

➡️ Ein System ohne **Selbstbeschreibung** gilt im Soll-Modell als **unvollständig**, auch wenn es technisch läuft.

---

### 3.3 Deterministische Verantwortung

Für jede Aktion **muss** es geben:

* eine Quelle (Mission / Trigger)
* eine Entscheidung (Regel / Modell / Heuristik)
* ein Ergebnis (Output / Fehler)
* eine Zuordnung (Job-ID / Chain / Kontext)

> **„Ich weiß nicht, warum" ist kein akzeptabler Zustand.**

---

## 4. Soll-Architektur (konzeptionell)

### 4.1 Rollen (klar getrennt)

| Rolle     | Soll-Funktion              |
| --------- | -------------------------- |
| Core      | Entscheidung & Wahrheit    |
| Worker    | Ausführung                 |
| LLM       | Interpretation / Vorschlag |
| Mesh      | Verteilung / Skalierung    |
| Dashboard | Bewusstsein / Sichtbarkeit |

➡️ **Kein Modul darf zwei Rollen gleichzeitig sein.**

---

### 4.2 LLM im Soll-Zustand

LLMs **sollen**:

* austauschbar sein
* fehlertolerant eingebunden sein
* niemals allein entscheidend sein

LLMs **dürfen nicht**:

* Systemzustand definieren
* Wahrheit ersetzen
* stillschweigend scheitern

➡️ Das LLM ist **Berater**, nicht **Instanz**.

---

## 5. Soll-Zustände des Gesamtsystems

### 5.1 Zulässige Zustände

| Zustand     | Bedeutung                          |
| ----------- | ---------------------------------- |
| OPERATIONAL | Alles erfüllt                      |
| DEGRADED    | Funktionsfähig mit Einschränkungen |
| REFLECTIVE  | System analysiert sich selbst      |
| RECOVERY    | Kontrollierter Wiederaufbau        |
| PAUSED      | Bewusst gestoppt                   |

➡️ **CRASH** ist *kein* Soll-Zustand.

---

### 5.2 Übergänge (Pflicht)

Jeder Zustandswechsel **muss**:

* sichtbar sein
* begründet sein
* rückverfolgbar sein

---

## 6. Lernen & Evolution (klar begrenzt)

Sheratan **soll lernen**, aber:

| Erlaubt               | Nicht erlaubt                |
| --------------------- | ---------------------------- |
| Routing-Optimierung   | Zielmutation                 |
| Fehlervermeidung      | Werteverschiebung            |
| Performance-Anpassung | implizite Prioritätsänderung |
| Heuristik-Tuning      | Selbstzweck-Evolution        |

➡️ Lernen **innerhalb eines Rahmens**, nicht darüber hinaus.

---

## 7. Mensch–System-Beziehung (normativ)

Der Mensch ist im Soll-Modell:

* **Zielgeber**
* **Grenzsetzer**
* **letzte Instanz**

Sheratan ist:

* **Ausführer**
* **Beobachter**
* **Reflektor**

➡️ **Sheratan darf widersprechen.**
➡️ **Sheratan darf nicht überstimmen.**

---

## 8. Formale Soll-Aussage

> **Sheratan erfüllt seinen Soll-Zustand, wenn:**

1. es funktionsfähig ist (**Ist**)
2. es sich selbst beschreiben kann
3. es Abweichungen erkennt
4. es kontrolliert reagiert
5. es ohne Bedeutungsverlust erweiterbar ist

---

## 9. Verhältnis Ist ↔ Soll (aktuelle Bewertung)

| Bereich              | Status        | Begründung                                    |
| -------------------- | ------------- | --------------------------------------------- |
| Operativer Kern      | ✅ erfüllt     | Core API, Worker, Mesh funktionieren          |
| End-to-End Sinnfluss | ✅ erfüllt     | Intent → Ausführung → Rückmeldung verifiziert |
| Selbstbeschreibung   | ⚠️ teilweise  | Dashboard zeigt Status, aber keine Reflexion  |
| Zustandsmodell       | ⚠️ implizit   | Zustände existieren, aber nicht formalisiert  |
| Evolution            | ⏳ vorbereitet | Architektur erlaubt Erweiterung               |

➡️ **Ist ≈ 70–75 % Soll**, ohne Architekturbruch.
Das ist **sehr hoch**.

---

## 10. Warum diese Soll-Definition wichtig ist

Ab jetzt kannst du **formale Fragen stellen**, z. B.:

* „Ist Sheratan gerade OPERATIONAL oder nur DEGRADED?"
* „Welche Soll-Eigenschaft verletzt dieser Bug?"
* „Ist diese Erweiterung Soll-konform oder nur Feature-Zuwachs?"

Das ist der Punkt, an dem Systeme **erwachsen** werden.

---

## 11. Implementierungspfade (priorisiert)

### Phase A: Selbstbeschreibung (kritisch)

**Ziel:** System kann seinen eigenen Zustand formal beschreiben

**Maßnahmen:**
1. Zustandsautomat implementieren (`OPERATIONAL`, `DEGRADED`, `REFLECTIVE`, `RECOVERY`, `PAUSED`)
2. State-Transition-Logging
3. `/api/system/state` Endpoint mit Begründung
4. Dashboard: Zustandsanzeige mit Historie

**Aufwand:** 4-6 Stunden  
**Priorität:** HOCH (schließt Soll-Lücke)

---

### Phase B: Deterministische Verantwortung (wichtig)

**Ziel:** Jede Aktion ist rückverfolgbar

**Maßnahmen:**
1. Erweiterte Job-Metadaten (Quelle, Entscheidungsgrund, Kontext)
2. Decision-Log (warum wurde dieser Worker gewählt?)
3. Chain-of-Custody für Ergebnisse
4. Audit-Trail-Visualisierung im Dashboard

**Aufwand:** 6-8 Stunden  
**Priorität:** MITTEL (verbessert Beobachtbarkeit)

---

### Phase C: LLM-Fallback & Routing (robustheit)

**Ziel:** LLM-Ausfälle degradieren System, brechen es nicht

**Maßnahmen:**
1. Multi-LLM-Routing (ChatGPT → Gemini → Fallback)
2. Timeout-Handling mit Retry-Logik
3. Degraded-Mode bei LLM-Ausfall
4. LLM-Health-Monitoring

**Aufwand:** 5-7 Stunden  
**Priorität:** MITTEL (erhöht Resilienz)

---

### Phase D: Reflexive Capabilities (fortgeschritten)

**Ziel:** System kann sich selbst analysieren

**Maßnahmen:**
1. Self-Diagnostic-Jobs (System analysiert eigene Logs)
2. Anomalie-Detektion (unerwartete Zustandsübergänge)
3. Performance-Baseline-Tracking
4. Automated Health Reports

**Aufwand:** 8-12 Stunden  
**Priorität:** NIEDRIG (evolutionär, nicht kritisch)

---

## 12. Nächste logische Schritte

### Option 1: Abweichungsmatrix Ist ↔ Soll
Systematische Auflistung aller Soll-Eigenschaften mit Ist-Status und Implementierungspfad

### Option 2: Zustandsautomat formal definieren
State Machine mit Übergangsbedingungen, Ereignissen und Invarianten

### Option 3: Fail-Simulation entlang der Soll-Grenzen
Kontrolliertes Testen der Degradationszustände und Fehlertoleranz

---

**Dokumentversion:** 1.0  
**Status:** Normativ  
**Basis:** [SYSTEM_IST_DEFINITION.md](SYSTEM_IST_DEFINITION.md)  
**Nächste Review:** Nach Implementierung Phase A
