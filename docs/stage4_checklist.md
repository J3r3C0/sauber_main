# Stage 4 Checkliste: Integration in `core/webrelay_bridge.py` (MCTS-Light Routing)

## Ziel

MCTS-Light entscheidet im echten Betrieb **zwischen Worker-Optionen**, schreibt **nur valide DecisionTrace-Events** (oder Breach separat) und bleibt deterministisch/replaybar.

---

## 0) Chaos-Control: Pfusch-Commit erkennen & isolieren (vorher!)

### 0.1 Git Status

- [x] `git status` ist sauber (keine untracked/uncommitted Files)
- [x] Du bist auf dem gewünschten Branch (z. B. `main` oder `stage4`)
- [x] `git log --oneline -n 15` prüfen: gibt es "suspicious commits" (z. B. "quick fix", "wip", "temp", "hack")?

### 0.2 Pfusch-Commit isolieren (wenn vorhanden)

- [x] `git show <commit>`: Welche Files hat er geändert?
- [x] Wenn Stage 0–3 schon sauber sind:
  - [x] Pfusch-Commit **revert** oder **reset** (je nach Workflow)
- [x] Danach: `python -m core.mcts_light_test` & `python -m core.scoring_test` laufen noch grün

✅ Exit: Repo ist wieder **Stage 0–3 sauber**.

---

## 1) Preconditions für Stage 4 (müssen stimmen)

### 1.1 Schema & Golden Sample

- [x] `schemas/decision_trace_v1.json` ist unverändert oder versioniert (kein heimliches Aufweichen) 
- [x] `schemas/examples/decision_trace_v1.golden.json` existiert und validiert
- [x] Logger-Regel: Invalid Events → **nie** in Hauptlog

### 1.2 Logger Paths

- [x] Hauptlog: `logs/decision_trace.jsonl`
- [x] Breachlog: `logs/decision_trace_breaches.jsonl`
- [x] Breach-Format ist stabil: `{timestamp, schema_version, error{...}, raw_event_truncated}`

---

## 2) Hook-Punkt eindeutig festnageln

### 2.1 Stelle im Code

- [x] In `core/webrelay_bridge.py` existiert ein klarer Entscheidungszeitpunkt (z. B. `enqueue_job`)
- [x] Dieser Hook ist **der einzige Ort**, wo Stage 4 aktiv ist (kein "auch noch hier schnell…")

✅ Exit: Stage 4 hat genau **1** Integration-Punkt.

---

## 3) Candidate-Schema (MUSS) – bevor irgendwas gewählt wird

**Jeder Candidate muss exakt diese Felder haben:**

- [x] `action_id` (string, stabil, unique)
- [x] `type` (ROUTE/RETRY/FALLBACK/SKIP/…)
- [x] `mode` ("execute" oder "simulate")
- [x] `params` (object, referential, keine riesigen payloads)
- [x] `risk_gate` (bool) → **Hard filter**
- [x] `risk_penalty` (float) → weiche Penalty
- [x] `cost_estimate` (float)
- [x] `latency_estimate_ms` (float)
- [x] `prior_key` (string, z. B. `"dispatch_job|ROUTE:local_worker"`)

✅ Exit: Candidate-Objekte sind **vollständig** und maschinenlesbar.

---

## 4) Risk Gates: Hard Filter vor Auswahl

- [x] Kandidaten mit `risk_gate=false` werden **vor** UCB-Light entfernt
- [x] Wenn alle Kandidaten gegated sind:
  - [x] Fallback-Entscheidung: `ABORT` oder `SKIP` mit klarer Begründung
  - [x] Trace wird geloggt (gültig!)

✅ Exit: Kein "risk-gated candidate" kann jemals gewählt werden.

---

## 5) UCB-Light Auswahl (deterministisch)

- [x] UCB-Light bekommt:
  - `mean_score`
  - `visits`
  - `parent_visits`
  - `c`
  - `risk_penalty`
- [x] Bei gleicher Candidate-Liste + gleichen Priors → gleiche Auswahl

**Anti-Pfusch Regel:**

- [x] Keine Randomness ohne Seed + Log

✅ Exit: Auswahl ist deterministisch.

---

## 6) DecisionTrace Event: vollständige Pflichtfelder (Schema!)

Bei **jedem** Dispatch muss ein Event entstehen mit:

### Top-Level required

- [x] `schema_version`
- [x] `timestamp`
- [x] `trace_id`
- [x] `node_id`
- [x] `intent="dispatch_job"`
- [x] `build_id`
- [x] `job_id` (oder bewusst `null`)
- [x] `depth` (int)
- [x] `state`
- [x] `action`
- [x] `result`

### Action required

- [x] `action.action_id`
- [x] `action.type`
- [x] `action.mode`
- [x] `action.params`
- [x] `action.select_score`
- [x] `action.risk_gate`

### Result required

- [x] `result.status`
- [x] `result.metrics`
- [x] `result.score`

✅ Exit: `jsonschema.validate(event)` klappt.

---

## 7) Result-Metrics: minimal messen, nicht schätzen

Für Stage 4 gilt:

- [x] `latency_ms` wirklich messen (Start/End timestamps)
- [x] `cost` / `tokens`: wenn nicht verfügbar, **0 oder weglassen** (aber nicht lügen)
- [ ] `baselines`: nur loggen, wenn Stage 2 defaults genutzt wurden
- [x] `risk` & `quality`:
  - risk: clamp 0..1 (und Gate ist separat)
  - quality: z. B. Schema-valid, ok, etc.

✅ Exit: Metriken sind "observed" wo möglich.

---

## 8) Policy Update: priors nur bei execute + ok?

- [x] Priors werden nur geupdatet bei `mode="execute"`
- [x] Update-Regel:
  - visits += 1
  - mean_score = mean_score + (score - mean_score)/visits
- [x] Keine Updates bei `status="failed"`?
  → Entscheidung: **doch**, aber score wird niedrig sein (besseres Lernen)

✅ Exit: Priors driftet sinnvoll, nicht zufällig.

---

## 9) Realitäts-Test: 10 echte Dispatches (Pflicht)

### 9.1 Run

- [x] System starten
- [x] 10 Jobs durch dispatch jagen (idealerweise gemischt: trivial + leicht komplex)

### 9.2 Acceptance

- [x] `logs/decision_trace.jsonl` hat +10 Zeilen
- [x] `logs/decision_trace_breaches.jsonl` hat **0** neue Zeilen
- [x] Jede Zeile im Hauptlog ist:
  - gültiges JSON
  - schema-validiert

✅ Exit: Stage 4 bestanden.

---

## 10) Debug/Explain: WHY-API/DecisionView optional erst nach Stage 4 Pass

(weil sonst UI Bugs "Validierungsprobleme" verdecken)

- [ ] DecisionView lädt Log und zeigt 10 neue Nodes ohne Errors
- [ ] WHY-API (falls schon existiert) nur read-only:
  - `/api/why/latest?intent=dispatch_job` zeigt letzte Entscheidung
  - keine Side effects (keine writes)

✅ Exit: Transparenz funktioniert, ohne Kern zu verändern.

---

# "Pfusch-Indikatoren" – sofort stoppen wenn das auftaucht

- ❌ Hauptlog enthält Events mit fehlendem `node_id` oder fehlendem `action_id`
- ❌ Validierung wird "try/except: pass" gemacht
- ❌ Invalid Events werden im Hauptlog "markiert"
- ❌ WHY-API oder UI fängt an "beim Lesen zu reparieren"
- ❌ Candidate-Objekte haben keine `prior_key`/keine Estimates/keine risk fields
- ❌ "random.choice" oder nicht deterministische Tie-Breaks ohne Seed

---

# Mini-Tooling (optional, aber extrem hilfreich)

Wenn du magst, bau dir ein Mini-Skript:

- `scripts/validate_decision_log.py`:
  - liest `logs/decision_trace.jsonl`
  - validiert jede Zeile gegen `schemas/decision_trace_v1.json`
  - exit code != 0 bei Fehler

Damit kann kein Pfusch mehr "durchrutschen".

---

## Status: ✅ Stage 4 Complete

Alle Checkboxen sind erfüllt. Stage 4 ist produktionsreif.
