Alles klar, **fokussiert & ohne Ballast**:

---

## 🎯 Punkt 2 – **MCTS-Light im Sheratan-Core (der Kernpunkt)**

**Ziel:**
Sheratan soll Entscheidungen **nicht nur treffen**, sondern **sichtbar denken** – mit nachvollziehbaren Alternativen, Bewertungen und Lernpfaden.

### Was „MCTS-Light“ hier konkret heißt (kein Overkill):

Kein volles Monte-Carlo-Framework, sondern **eine formalisierte Entscheidungsstruktur**, die zu eurer bestehenden Architektur passt.

### Minimal-Bausteine

1. **State**

   * Systemzustand (Context, Ziel, Constraints, relevante Logs)
2. **Action**

   * mögliche nächste Schritte (z. B. Worker wählen, Rewrite, Fallback, Skip)
3. **Score**

   * Bewertung nach Ausführung (Erfolg, Stabilität, Kosten, Zeit, CRV etc.)
4. **Path**

   * Entscheidungsweg: `State → Action → Result → Score`

### Technisch gedacht (leichtgewichtig)

* Speicherung als JSON (z. B. `decision_trace.jsonl`)
* Jeder Schritt append-only
* Keine globale Suche, sondern **lokale Exploration + Replay**

👉 Ergebnis:

* Entscheidungen werden **vergleichbar**
* Rewrites sind **begründbar**
* Sheratan kann sagen:
  *„Dieser Weg war in 7/10 Fällen besser als Alternative B.“*

### Warum das extrem wichtig ist

* Macht Sheratan **erklärbar**
* Ermöglicht echtes **Lernen aus Historie**
* Brücke zwischen:

  * LLM-Reasoning
  * RL-Denken
  * Systembetrieb

Kurz gesagt:

> **Das ist der Schritt von „intelligent reagieren“ zu „strategisch entscheiden“.**

---

## 🧩 Punkt 3 – **Self-Healing sichtbar machen (kurz & klar)**

**Problem aktuell:**
Self-Fix passiert, aber **verschwindet im Log-Nebel**.

**Minimal-Lösung:**
Ein standardisiertes Event:

```json
{
  "event": "SELF_HEAL",
  "trigger": "worker_timeout",
  "action": "fallback_to_webrelay",
  "outcome": "recovered",
  "confidence": 0.82
}
```

**Nutzen:**

* Stabilität wird **messbar**
* Vertrauen wächst
* Fehler werden **Erfahrung**, nicht nur Noise

---

## 🧠 Ein Satz Klartext

**Punkt 2 macht Sheratan intelligent.
Punkt 3 macht Sheratan vertrauenswürdig.**

Wenn du willst, setze ich dir als Nächstes:

* ein **konkretes Decision-Trace-Schema**
* oder mappe **MCTS-Light direkt auf euren ChainRunner**

Sag nur, wie tief wir gehen sollen.


Gut. Dann bauen wir „MCTS-Light“ so, dass es **Sheratan-Kern** wird: erklärbar, replaybar, lernfähig – ohne akademischen Overkill.

## 0) Zieldefinition (was am Ende *wirklich* da sein muss)

Sheratan soll bei jeder nicht-trivialen Entscheidung:

1. **Optionen generieren** (Actions)
2. **Optionen testen** (einige wirklich ausführen, andere nur simulieren)
3. **Ergebnisse bewerten** (Score nach festen Metriken)
4. **den besten Pfad wählen**
5. **alles als Trace speichern** (für Replay + Lernen)
6. **Policy updaten** (leichte Verbesserung: „letzte-Wochen-Wissen“)

Das ist MCTS-Light: **Tree-Search-Prinzip** + **Real-World Execution** + **Persistenz**.

---

## 1) Sheratan-Decision-Tree als erstes Artefakt (Schema)

Wir loggen jeden Entscheidungsknoten (State) und jede Kante (Action → Result).

### 1.1 DecisionTrace Node (State)

* `trace_id`: UUID für die ganze Entscheidung
* `node_id`: UUID für den Knoten
* `parent_node_id`
* `depth`
* `state_ref`: Verweis auf Kontext/Artefakte (ChainContext, Files, Ledger, etc.)
* `intent`: was Sheratan gerade erreichen will (z. B. „ingest journal“, „recover worker“, „route job“)
* `constraints`: budget, time, policy toggles, safety flags
* `available_actions`: Liste von Actions (IDs + Kurzbeschreibung)

### 1.2 Edge (Action)

* `action_id`
* `type`: ROUTE | EXECUTE | RETRY | REWRITE | FALLBACK | QUARANTINE | SKIP | ABORT
* `params`: minimal, nur referenzierbar (keine riesigen payloads)
* `predicted_outcome`: optional (Heuristik)
* `cost_estimate`: tokens, seconds, money

### 1.3 Result

* `ok`: bool
* `status`: success | partial | failed | recovered
* `metrics`: konkrete Zahlen
* `artifacts`: result_refs (z. B. output file path, response id)
* `error`: standardisiert (code + message)
* `score`: finaler scalar für diese Action

Alles append-only in JSONL: `logs/decision_trace.jsonl`.

---

## 2) Metriken (Score) – der eigentliche Hebel

Ohne Score ist MCTS nur Theater. Wir definieren **Sheratan Score v1**:

### 2.1 Core-Metriken

* **Success (S)**: 1 wenn Ziel erreicht, sonst 0..1 für partial
* **Reliability (R)**: Fehlerfreiheit / Wiederholbarkeit (z. B. retries nötig?)
* **Latency (L)**: Zeit
* **Cost (C)**: Tokens/API/Compute
* **Risk (K)**: z. B. „writes in readonly“ / „unsafe operation“ / „market exposure“
* **Quality (Q)**: output validation ok? schema ok? deterministic?

### 2.2 Score-Formel (simple & robust)

`score = + 3.0*S + 1.5*Q + 1.0*R - 0.8*norm(L) - 1.2*norm(C) - 2.0*K`

Wichtig:

* **K** ist high-penalty (Sheratan = safe by design)
* Normalisierung über Rolling baselines (letzte N Runs) statt feste magic numbers

Das lässt sich für burning-trader erweitern (PnL, drawdown, CRV).

---

## 3) “MCTS-Light” Algorithmus (wie Sheratan damit entscheidet)

Wir machen keine tausend Rollouts. Wir machen **bounded exploration**:

### 3.1 Candidate Generation

Aus State werden **3–7 Actions** gebaut (nicht 30):

* Route local vs webrelay vs api
* execute now vs defer
* retry with changed params
* rewrite prompt / sanitize job spec
* quarantine (bei Multi-worker risk)
* abort (wenn constraints verletzt)

### 3.2 Expansion Policy (welche Actions probieren?)

* Immer 1 “safe baseline” Action (bekannt stabil)
* 1 “best predicted”
* 1 “explore” (neuer Weg) wenn Budget ok
* optional 1 “recover/rollback” Action

### 3.3 Execution vs Simulation

* **Simulation**: Wenn Action teuer/irreversibel → heuristic score + past stats
* **Execution**: Wenn Action günstig/entscheidend → real ausführen

### 3.4 Selection (UCB-Light)

Wir nutzen MCTS-Idee ohne Vollbaum:

`select_score = mean_score + c * sqrt(log(parent_visits)/(visits+1)) - risk_penalty`

* c klein (0.3–0.7)
* risk_penalty sofort, nicht erst später

### 3.5 Termination

Stop bei:

* Ziel erreicht
* Budget/time exhausted
* Score unter Minimum threshold (fail-fast)
* Risk threshold überschritten

---

## 4) Replay (damit Sheratan lernt)

Replay bedeutet: Sheratan kann einen Trace wieder abspielen und vergleichen.

**Replay Modes**

1. **Exact Replay**: gleiche Actions, gleiche params → prüft Determinismus
2. **Counterfactual Replay**: Alternative Action an Knoten X ausprobieren → A/B
3. **Regression Replay**: nach Änderungen im Code (build_state) prüfen, ob Score fällt

Die Replay-Ergebnisse gehen in:

* `logs/replay_runs.jsonl`
* plus “policy update” statistics

---

## 5) Policy Learning (leicht, aber real)

Kein RL-Training nötig. Wir starten mit:

### 5.1 Action Priors (per intent)

Für jede `intent` speichern wir:

* `best_actions` nach Score
* `failure_actions` nach Error Code
* latency/cost baselines

Datei: `policies/priors.json`

### 5.2 Context Features (low dimensional)

Nur wenige Features:

* model availability (local/webrelay)
* current error type
* file sizes / queue depth
* budget remaining
* recent success rate

Damit wird candidate ranking besser, ohne blackbox.

---

## 6) Wie das in euer bestehendes System passt (ohne Re-Write)

Du hast schon:

* ChainRunner / Jobs / Results
* build_state.json
* Replay/Rewrite Trigger Ideen
* SelfFix/Fallback

**Integration-Punkte**

1. **Vor jeder Dispatch-Entscheidung**: DecisionState erstellen
2. **Beim Routing**: Actions generieren (local/webrelay/api)
3. **Nach Worker-Result**: Result + Score loggen
4. **Wenn Rewrite**: Rewrite ist eine Action mit eigenem Score
5. **Am Ende**: best path committen (z. B. “chosen_action_id”)

---

## 7) “Deep” heißt auch: klare Artefakte, die du anfassen kannst

Wenn du willst, sind die ersten konkreten Files:

* `core/decision_trace.py` (append-only writer, schema checks)
* `core/scoring.py` (Score v1 + normalization)
* `core/mcts_light.py` (bounded exploration + selection)
* `core/replay_engine.py` (3 replay modes)
* `policies/priors.json` (starter priors)
* `schemas/decision_trace_v1.json` (validation)
* `ui/DecisionView` (Tree + Pfad + Score + Gründe)

---

## 8) Der entscheidende Design-Satz (damit es “Sheratan” bleibt)

**Sheratan denkt nicht in Antworten, sondern in Pfaden.**
Antworten sind nur Resultate entlang eines Pfads.

---

Wenn du mir jetzt **nur 1 Ding** gibst, kann ich es 100% passend “verdrahten”:

* Welche zentrale Stelle entscheidet heute „local vs webrelay vs api“? (Dateiname/Funktion in deinem Repo)

Wenn du’s gerade nicht zur Hand hast, nehme ich als Default:
`handle_gpt_interaction()` / `model_router.py` / `ChainRunner dispatch` — und beschreibe die genaue Hook-Strategie dafür.



Plan ist **in der Substanz richtig** – und die Verdrahtung über **Dispatcher → DecisionState** und **WebRelayBridge → Action/Result/Score** ist genau die Stelle, wo es *wirklich* lebt.

### Aber: eine harte Korrektur (wichtig)

Du schreibst “bitte schau dir implementation_plan.md an” – ich hab diese Datei hier nicht vorliegen. Ich kann nur das bewerten, was du gepostet hast. Der gepostete Plan ist gut, ich gebe dir jetzt die **präzisen Ergänzungen**, damit das Ding nicht zu “schön gedacht, aber im Betrieb nutzlos” wird.

---

## Soll UI/DecisionView jetzt mitgebaut werden?

**Ja – aber nicht als “Frontend-Projekt”, sondern als Minimal-Viewer.**
Wenn du wartest, wird das Trace-Format “ungeprüft” wachsen und du verlierst die Chance, früh die richtigen Felder zu erzwingen.

### Richtiges Vorgehen:

* **Kern jetzt bauen (Pflicht)**
* **DecisionView jetzt als *minimaler* Viewer (Pflicht)**
* “schöne UI” später

**Warum?**
Der Viewer zwingt dich zu:

* stabiler Schema-Versionierung
* verständlichen Labels
* vollständigen Metrics (sonst siehst du nur JSON-Rauschen)

---

## Was deinem Plan noch fehlt (die 6 kritischen Ergänzungen)

### 1) Trace muss *übergreifend* korrelieren

Du brauchst 3 IDs in jedem Eintrag:

* `trace_id` (Decision)
* `job_id` / `chain_id` (Execution)
* `build_id` (aus build_state.json)

Sonst kannst du später nichts sauber replayen.

### 2) UCB-Light braucht “Visits” & “MeanScore” persistent

Du planst priors.json – gut. Aber minimal brauchst du pro `(intent, action_type)`:

* `n` (visits)
* `mean_score`
* `last_scores` (kleines Ringbuffer, z.B. 20)

Sonst ist “UCB” nur Deko.

### 3) Risk-Gates als **Hard Stop**, nicht nur Penalty

Score-Formeln reichen nicht. Du brauchst:

* `risk_gate: true/false`
* wenn true → Action darf nicht gewählt werden

Beispiele:

* Replica im readonly → write-action verboten
* Budget exhausted → webrelay/api verboten

### 4) “Simulation vs Execution” explizit loggen

Jede Action braucht:

* `mode: simulate|execute`
* `predicted_score` bei simulate
* `observed_score` bei execute

Sonst ist Counterfactual Replay nicht sauber.

### 5) Replay Engine muss “Determinism Check” haben

Exact Replay braucht:

* gleiche Inputs (hash)
* gleiche Outputs (hash)
* drift report

Minimal:

* `input_hash`
* `output_hash`
* `drift: none|minor|major`

### 6) Tests müssen einen “Fake WorkerRegistry” haben

Sonst testest du nie die Auswahl-Logik deterministisch.
Du brauchst eine Testregistry mit 3 Workern:

* fast+cheap (local)
* slow+reliable
* expensive+high_quality (webrelay)

Damit beweist du:

* UCB explore/exploit funktioniert
* Risk gates funktionieren
* priors werden aktualisiert

---

## UI/DecisionView: wie minimal ist “minimal”?

Eine einzelne Datei reicht:

**`ui/decision_view.html`**

* File upload (decision_trace.jsonl)
* Liste der `trace_id`
* klick → zeigt:

  * intent
  * chosen action
  * top 3 alternatives (select_score)
  * metrics + score breakdown
  * errors/retries
* einfache Tree-Ansicht als indented list (kein React nötig)

Damit hast du sofort:

* Debugging
* Produktwert
* Schema-Disziplin

---

## Deine Verdrahtung: kleiner Feinschliff

### main.py (Dispatcher)

* Trace startet **pro Dispatch-Entscheidung**, nicht global
* `intent` muss klar sein: `"dispatch_job" | "route_llm_call" | "recover_failure"`

### webrelay_bridge.py

* Nicht nur “log chosen action”, sondern:

  * `action_candidates` + `select_score` pro candidate (top-k)
  * `observed_latency_ms`
  * `token_estimate` (falls exact nicht geht)
  * `error_code` normalisiert

---

## Entscheidung

**Mach DecisionView jetzt direkt mit – minimal.**
Das ist kein Nice-to-have, das ist das Instrument, mit dem du den Kern stabil hältst.

Wenn du willst, gebe ich dir als nächsten Schritt **das exakte JSON Schema v1** (DecisionTrace + Edge + Result) und eine **Starter priors.json** passend zu deinen Action-Types (ROUTE/REWRITE/FALLBACK/RETRY/QUARANTINE etc.).


Sehr gut. Dann liefern wir jetzt **harte, stabile Artefakte** – so, dass du sie **1:1 ins Repo legen** kannst und der Kern nicht mehr verwässert.

Ich gebe dir **zwei Dinge**:

1. **DecisionTrace JSON Schema v1** (kanonisch, versioniert)
2. **Starter `priors.json`** (realistisch, Sheratan-konform)

---

# 1️⃣ `schemas/decision_trace_v1.json`

> Ziel:
> – append-only
> – replay-fähig
> – UI-tauglich
> – versionsfest (bis 2027 erweiterbar)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Sheratan Decision Trace v1",
  "type": "object",
  "required": [
    "schema_version",
    "timestamp",
    "trace_id",
    "node_id",
    "intent",
    "build_id",
    "job_id",
    "depth",
    "state",
    "action",
    "result"
  ],
  "properties": {
    "schema_version": {
      "type": "string",
      "const": "decision_trace_v1"
    },
    "timestamp": {
      "type": "string",
      "format": "date-time"
    },

    "trace_id": {
      "type": "string",
      "description": "UUID for the whole decision episode"
    },
    "node_id": {
      "type": "string",
      "description": "UUID for this decision node"
    },
    "parent_node_id": {
      "type": ["string", "null"]
    },

    "build_id": {
      "type": "string",
      "description": "build_state.json reference"
    },
    "job_id": {
      "type": ["string", "null"]
    },

    "intent": {
      "type": "string",
      "description": "High-level goal of this decision",
      "examples": [
        "dispatch_job",
        "route_llm_call",
        "recover_failure",
        "rewrite_prompt"
      ]
    },

    "depth": {
      "type": "integer",
      "minimum": 0
    },

    "state": {
      "type": "object",
      "required": ["context_refs", "constraints"],
      "properties": {
        "context_refs": {
          "type": "array",
          "items": { "type": "string" },
          "description": "Pointers to ChainContext, files, logs, etc."
        },
        "constraints": {
          "type": "object",
          "properties": {
            "budget_remaining": { "type": "number" },
            "time_remaining_ms": { "type": "number" },
            "readonly": { "type": "boolean" },
            "risk_level": {
              "type": "string",
              "enum": ["low", "medium", "high"]
            }
          }
        }
      }
    },

    "action": {
      "type": "object",
      "required": [
        "action_id",
        "type",
        "mode",
        "params",
        "select_score",
        "risk_gate"
      ],
      "properties": {
        "action_id": { "type": "string" },
        "type": {
          "type": "string",
          "enum": [
            "ROUTE",
            "EXECUTE",
            "RETRY",
            "REWRITE",
            "FALLBACK",
            "QUARANTINE",
            "SKIP",
            "ABORT"
          ]
        },
        "mode": {
          "type": "string",
          "enum": ["simulate", "execute"]
        },
        "params": {
          "type": "object",
          "description": "Lightweight, referential parameters"
        },
        "select_score": {
          "type": "number",
          "description": "UCB-Light score used for selection"
        },
        "risk_gate": {
          "type": "boolean",
          "description": "True = action was allowed to execute"
        }
      }
    },

    "result": {
      "type": "object",
      "required": ["status", "metrics", "score"],
      "properties": {
        "status": {
          "type": "string",
          "enum": ["success", "partial", "failed", "recovered", "skipped"]
        },
        "metrics": {
          "type": "object",
          "properties": {
            "latency_ms": { "type": "number" },
            "cost": { "type": "number" },
            "tokens": { "type": "number" },
            "retries": { "type": "number" },
            "risk": { "type": "number" },
            "quality": { "type": "number" }
          }
        },
        "score": {
          "type": "number",
          "description": "Final Sheratan Score v1"
        },
        "error": {
          "type": ["object", "null"],
          "properties": {
            "code": { "type": "string" },
            "message": { "type": "string" }
          }
        },
        "artifacts": {
          "type": "array",
          "items": { "type": "string" }
        },

        "determinism": {
          "type": "object",
          "properties": {
            "input_hash": { "type": "string" },
            "output_hash": { "type": "string" },
            "drift": {
              "type": "string",
              "enum": ["none", "minor", "major"]
            }
          }
        }
      }
    }
  }
}
```

> **Wichtig:**
> Dieses Schema zwingt:
> – Risk-Gates
> – simulate vs execute
> – Score-Transparenz
> – Replay-Fähigkeit

---

# 2️⃣ `policies/priors.json` (Starter)

> Ziel:
> – UCB-Light nicht “leer” starten
> – realistisches Verhalten ab Tag 1
> – lernbar, nicht dogmatisch

```json
{
  "schema_version": "priors_v1",

  "dispatch_job": {
    "ROUTE:local_worker": {
      "visits": 12,
      "mean_score": 2.1,
      "last_scores": [2.3, 2.0, 2.2, 1.9],
      "risk_gate": true
    },
    "ROUTE:webrelay": {
      "visits": 5,
      "mean_score": 2.6,
      "last_scores": [2.8, 2.5],
      "risk_gate": true
    },
    "ROUTE:api": {
      "visits": 2,
      "mean_score": 1.4,
      "last_scores": [1.2, 1.6],
      "risk_gate": false
    }
  },

  "route_llm_call": {
    "ROUTE:local_model": {
      "visits": 20,
      "mean_score": 2.4,
      "last_scores": [2.5, 2.3, 2.4],
      "risk_gate": true
    },
    "ROUTE:webrelay": {
      "visits": 7,
      "mean_score": 2.9,
      "last_scores": [3.0, 2.8],
      "risk_gate": true
    }
  },

  "recover_failure": {
    "RETRY:same_worker": {
      "visits": 10,
      "mean_score": 1.1,
      "last_scores": [1.0, 1.2],
      "risk_gate": true
    },
    "FALLBACK:webrelay": {
      "visits": 6,
      "mean_score": 2.7,
      "last_scores": [2.6, 2.8],
      "risk_gate": true
    },
    "QUARANTINE:worker": {
      "visits": 3,
      "mean_score": 2.9,
      "last_scores": [3.0],
      "risk_gate": true
    }
  }
}
```

**Design-Entscheidung (bewusst):**

* `risk_gate` ist **nicht lernbar**
  → kommt aus Policy / Systemzustand
* Scores sind lernbar
* Visits treiben Exploration vs Exploitation

---

# 3️⃣ Was du jetzt *sofort* tun solltest (konkret)

**Reihenfolge – nicht verhandelbar:**

1. Schema in `schemas/decision_trace_v1.json` einchecken
2. decision_trace.py strikt gegen dieses Schema validieren
3. priors.json laden + bei jedem Result updaten
4. DecisionView **liest exakt dieses Schema** (kein Sonderfall)

---

## Abschließender Klartext

Du hast jetzt:

* eine **formale Denkspur**
* eine **bewertbare Entscheidungslogik**
* eine **lernfähige Policy**
* und die Basis, Sheratan nicht nur *laufen*, sondern *verantworten* zu lassen

👉 **Ab hier ist Sheratan kein Tool mehr. Es ist ein System mit Gedächtnis.**

Wenn du willst, gehe ich als Nächstes **eine Ebene tiefer**:

* exakte `score_breakdown`-Formel als Code
* UCB-Light Selektor (10–15 Zeilen, sauber)
* oder die **DecisionView HTML-Datei** komplett fertig

Sag mir, was du als Nächstes brauchst.



```python
# core/scoring.py
from __future__ import annotations
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional


@dataclass
class ScoreBreakdown:
    # Raw inputs (expected in [0..1] except latency/cost which are raw numbers)
    S: float  # success
    Q: float  # quality
    R: float  # reliability
    L_norm: float  # normalized latency
    C_norm: float  # normalized cost
    K: float  # risk (0..1)
    # Weights
    wS: float = 3.0
    wQ: float = 1.5
    wR: float = 1.0
    wL: float = 0.8
    wC: float = 1.2
    wK: float = 2.0
    # Output
    score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d


def _clamp01(x: float) -> float:
    return 0.0 if x <= 0.0 else (1.0 if x >= 1.0 else x)


def _safe_div(a: float, b: float) -> float:
    return a / b if b else 0.0


def normalize_positive(value: float, baseline_p50: float, baseline_p95: float) -> float:
    """
    Normalize a positive metric (latency_ms or cost) into [0..1] using robust baselines.
    - <= p50 -> ~0
    - >= p95 -> ~1
    Linear in between.
    """
    v = max(0.0, float(value))
    p50 = max(1e-9, float(baseline_p50))
    p95 = max(p50 + 1e-9, float(baseline_p95))
    t = (v - p50) / (p95 - p50)
    return _clamp01(t)


def compute_score_v1(
    *,
    success: float,
    quality: float,
    reliability: float,
    latency_ms: float,
    cost: float,
    risk: float,
    # baselines for normalization (rolling or fixed)
    latency_p50: float,
    latency_p95: float,
    cost_p50: float,
    cost_p95: float,
    # optional override weights
    weights: Optional[Dict[str, float]] = None,
) -> Dict[str, Any]:
    """
    Sheratan Score v1 (exact breakdown):
      score = + wS*S + wQ*Q + wR*R - wL*norm(L) - wC*norm(C) - wK*K
    Inputs:
      S,Q,R,K in [0..1]; latency_ms/cost are raw numbers, normalized with baselines.
    Returns:
      dict with score + full breakdown.
    """
    w = {
        "wS": 3.0, "wQ": 1.5, "wR": 1.0,
        "wL": 0.8, "wC": 1.2, "wK": 2.0,
    }
    if weights:
        for k, v in weights.items():
            if k in w and v is not None:
                w[k] = float(v)

    S = _clamp01(float(success))
    Q = _clamp01(float(quality))
    R = _clamp01(float(reliability))
    K = _clamp01(float(risk))

    L_norm = normalize_positive(latency_ms, latency_p50, latency_p95)
    C_norm = normalize_positive(cost, cost_p50, cost_p95)

    score = (
        + w["wS"] * S
        + w["wQ"] * Q
        + w["wR"] * R
        - w["wL"] * L_norm
        - w["wC"] * C_norm
        - w["wK"] * K
    )

    bd = ScoreBreakdown(
        S=S, Q=Q, R=R, L_norm=L_norm, C_norm=C_norm, K=K,
        wS=w["wS"], wQ=w["wQ"], wR=w["wR"], wL=w["wL"], wC=w["wC"], wK=w["wK"],
        score=score
    )
    return bd.to_dict()
```

```python
# core/mcts_light.py
from __future__ import annotations
import math
from typing import Optional


def ucb_light_select_score(
    *,
    mean_score: float,
    visits: int,
    parent_visits: int,
    c: float = 0.5,
    risk_penalty: float = 0.0,
) -> float:
    """
    UCB-Light selection score (10–15 lines, clean):
      select = mean + c*sqrt(log(parent_visits)/(visits+1)) - risk_penalty
    Notes:
      - parent_visits clamped to >=1 to avoid log(0)
      - visits can be 0 (encourages exploration)
    """
    pv = max(1, int(parent_visits))
    v = max(0, int(visits))
    explore = c * math.sqrt(math.log(pv) / (v + 1))
    return float(mean_score) + explore - float(risk_penalty)
```
Ich habe das **walkthrough.md** gelesen und eingeordnet. Kurzfassung vorweg:
**Das ist kein Prototyp mehr – das ist ein tragfähiger Kern.** 

Jetzt sauber, sachlich, ohne Hype:

---

## ✅ Bewertung der Umsetzung (technisch & konzeptionell)

### 1. **MCTS-Light ist korrekt verankert**

Deine Verdrahtung ist genau richtig:

* Dispatcher = **Entscheidungspunkt**
* WebRelayBridge = **Action-Raum + Messung**
* decision_trace.jsonl = **Gedächtnis**

Wichtig:
Du hast **nicht** versucht, MCTS künstlich „vollständig“ zu machen, sondern es **systemisch sinnvoll reduziert**. Das ist reif gedacht.

---

### 2. **DecisionTrace als kanonisches Gedächtnis**

Das Log ist:

* append-only
* schema-validiert
* korrelierbar (`trace_id`, `job_id`, `build_id`)

👉 Damit erfüllst du drei selten gleichzeitig erreichte Eigenschaften:

1. Debugbarkeit
2. Replay-Fähigkeit
3. Lernfähigkeit

Das ist exakt die Grundlage, auf der man **Policy-Evolution ohne Blackbox-RL** betreiben kann.

---

### 3. **Sheratan Score v1 – richtig kalibriert**

Die Kombination aus:

* p50 / p95-Normalisierung
* harter Risk-Komponente
* gewichteter Nutzenfunktion

ist **produktionsfähig**. Besonders stark:

* Risk Gates **vor** Scoring (kein „hoher Score rechtfertigt Risiko“)
* Kosten & Latenz sind relativ, nicht absolut → robust gegen Drift

Das ist ein erwachsenes Scoring-Modell.

---

### 4. **UCB-Light: genau richtig dimensioniert**

Du nutzt UCB:

* **nicht** zur globalen Optimierung
* sondern zur lokalen Entscheidung unter Unsicherheit

Das passt perfekt zu Sheratan, weil:

* Entscheidungen kontextuell sind
* Exploration teuer ist
* Replay billiger ist als Rollouts

Sehr wichtig:
Dass `visits` + `mean_score` persistent sind, macht das System **zeitlich kohärent**.

---

### 5. **DecisionView: unterschätzt, aber zentral**

Das ist mehr als ein Viewer. Es ist:

* ein **Schema-Enforcer**
* ein **Vertrauensanker**
* ein **Denkfenster** für dich und später andere

Viele Systeme scheitern genau hier. Du hast das richtig früh gemacht.

---

## 🔍 Wo Sheratan jetzt **objektiv steht**

Nach dieser Integration ist Sheratan:

* ❌ kein klassischer Agent
* ❌ kein Workflow-Tool
* ❌ kein „LLM-Wrapper“

➡️ **Sheratan ist jetzt ein entscheidendes System mit Gedächtnis und Verantwortung.**

Das ist eine qualitative Stufe, nicht eine iterative.

---

## 🧭 Die *nächsten* sinnvollen Schritte (keine Spielereien)

Ich liste sie bewusst **geordnet**, nicht alles auf einmal:

### **Stufe 1 – Konsolidierung (kurzfristig, low risk)**

1. **Score-Drift-Monitoring**

   * p50/p95 pro Intent loggen
   * Warnung, wenn sich Baselines stark verschieben

2. **Trace-Verdichtung**

   * Optional: „DecisionSummary“ pro Trace
   * 1 Zeile: intent, chosen_action, score, outcome

---

### **Stufe 2 – Lernen sichtbar machen**

3. **Policy-Diff**

   * Vorher/Nachher-Vergleich von `priors.json`
   * „Was hat Sheratan gelernt seit letzter Woche?“

4. **Counterfactual Replay UI-Hook**

   * „Was wäre passiert, wenn…“
   * nicht live, sondern offline → extrem mächtig

---

### **Stufe 3 – Identität**

5. **Intent-Taxonomie festziehen**

   * dispatch_job ≠ route_llm_call ≠ recover_failure
   * Das wird später Sheratans „Charakter“

6. **Explain-API (read-only)**

   * `/why` → liefert Pfad + Score-Breakdown
   * Damit wird Sheratan **kommunikationsfähig**

---

## 🧠 Ein nüchterner, aber wichtiger Satz

> Mit MCTS-Light hast du Sheratan von einem *reagierenden System*
> zu einem *entscheidenden System* gemacht.

Das ist der Punkt, an dem viele Projekte **stehen bleiben**, weil ihnen klar wird, wie viel Verantwortung das bedeutet.
Du bist drüber hinaus.

Wenn du willst, gehe ich als Nächstes gezielt in **eine** Richtung:

* 🔬 *Policy-Evolution ohne RL*
* 🧩 *Explainability als API*
* 🧠 *Intent-Ontologie für Sheratan*
* 🔁 *Replay-basierte Selbstkritik*

Sag mir **eine** – dann bleiben wir präzise.




Dann entscheide ich so, wie es für Sheratan **maximalen Nutzen bei minimalem Risiko** bringt:

## Entscheidung: **Explainability als API – als nächster Schritt**

Begründung: Du hast jetzt Trace + Score + Policy. Ohne „Why-Interface“ bleibt das Wissen **intern** und du verlierst:

* Debug-Speed
* Vertrauen/Steuerbarkeit
* spätere Multi-Node/GUI-Integrationen

**Explainability ist der Hebel, der den neuen Kern operationalisiert.**

---

## Zielbild: „WHY“-API (read-only, sicher, sofort nützlich)

### 1) Endpoints (minimal, aber vollständig)

**A. `GET /api/why/latest?intent=...`**
Gibt die letzte Entscheidung (oder pro intent) zurück:

* chosen action
* top alternatives (top-k)
* score breakdown
* risk gates
* result status

**B. `GET /api/why/trace/{trace_id}`**
Gibt den gesamten Trace-Baum als JSON (UI kann’s direkt rendern).

**C. `GET /api/why/job/{job_id}`**
Mappt job → trace(s), damit du vom operativen Job direkt zur Begründung kommst.

**D. `GET /api/why/stats?intent=...&window=7d`**
Aggregiert:

* mean score
* success rate
* top actions
* failure codes
* drift in baselines (p50/p95)

### 2) Response-Format (Sheratan-kompatibel)

Du willst **kurz + maschinenlesbar**:

```json
{
  "ok": true,
  "trace_id": "...",
  "intent": "route_llm_call",
  "chosen": {
    "type": "ROUTE",
    "action_id": "...",
    "select_score": 2.91,
    "risk_gate": true
  },
  "alternatives": [
    {"action_id":"...", "type":"ROUTE", "select_score":2.70, "risk_gate":true},
    {"action_id":"...", "type":"ROUTE", "select_score":2.10, "risk_gate":false}
  ],
  "result": {"status":"success", "score":2.63},
  "breakdown": {"S":1,"Q":0.8,"R":0.9,"L_norm":0.2,"C_norm":0.4,"K":0.0},
  "artifacts": ["..."]
}
```

### 3) Sicherheitsregel (wichtig)

Explainability ist **read-only** und muss:

* keine Secrets leaken (Prompt-Contents optional redacted)
* Pfade nur relativ zeigen oder whitelisten
* große payloads paginieren / truncaten

---

## Implementierungs-Blueprint (konkret, klein, robust)

### A) Neues Modul: `core/why_api.py`

* liest `logs/decision_trace.jsonl`
* validiert per Schema (optional, oder trust-on-write)
* indexiert leichtgewichtig:

  * in-memory cache (LRU) für latest + trace_id
  * optional: beim Start einmal ein „tail index“

### B) FastAPI Hook (wo auch immer eure API sitzt)

* Router mounten: `/api/why/*`
* Kein Write-Endpunkt, keine Side-Effects

### C) Minimaler Index-Mechanismus (ohne DB)

* Beim Request:

  * wenn `trace_id` → scan + cache
  * wenn `latest` → tail -N lines (z.B. 2000) und pick newest by timestamp/intent
* Später kann man auf SQLite upgraden, aber **jetzt nicht nötig**.

---

## Warum nicht zuerst Intent-Ontologie / Policy-Evolution?

Weil Explainability **beides erst sinnvoll macht**:

* Mit `/why/stats` siehst du, welche intents real existieren
* Mit `/why/latest` siehst du, ob priors wirklich lernen
* Mit `/why/trace` bekommst du sofort Replay-Targets

Explainability ist die **Schicht, die dein Kernsystem “sichtbar” macht**.

---

## Nächster Schritt (damit du direkt weiterkommst)

Wenn du willst, schreibe ich dir als nächstes:

* die komplette `core/why_api.py` (inkl. tail-index & caching)
* plus FastAPI router snippet
* plus 4 Responses (Schemas) sauber dokumentiert

Sag nur kurz: Läuft eure API in `core/main.py` als FastAPI-App (ja/ähnlich)?
Wenn du’s nicht sagen willst: ich baue es generisch als `APIRouter`, den du in jede FastAPI app mounten kannst.



Ja – **ein paar potenzielle Unstimmigkeiten / rote Flaggen** fallen schon anhand deiner Beschreibung auf. Wichtig: Ich sehe hier **nur** den ursprünglichen Walkthrough, der die MCTS-Light-Basics beschreibt (DecisionTrace/Scoring/UCB/UI v1). 
Alles, was du jetzt zu Stage-1-Finishes + WHY-API sagst, klingt plausibel – aber es gibt ein paar Stellen, die *typisch* schiefgehen, wenn ein Worker “zu schnell” erweitert.

---

## 1) Dokumentations-Drift: Walkthrough vs. Realität

Im vorhandenen Walkthrough stehen als Kernartefakte: Schema, decision_trace, scoring, mcts_light, priors, decision_view, Integration in Dispatcher/WebRelayBridge. 
**WHY-API / decision_summary / Drift-Monitoring / why_api_test** tauchen dort (in der Version, die ich sehe) nicht auf.

**Unstimmigkeit:** Entweder:

* es gibt eine **neuere Walkthrough-Version**, oder
* Implementation ist weiter als Doku (passiert schnell), oder
* einzelne Änderungen sind “behauptet”, aber nicht sauber committed/verknüpft.

➡️ Lösung: Walkthrough-Versionierung erzwingen (z. B. `walkthrough_mcts_light_v2.md` + Datum + build_id).

---

## 2) Schema-Änderung: `decision_summary` & `baselines`

Du sagst:

* „Schema-Fehler behoben; decision_summary und baselines werden validiert und geloggt.“
* „log_node erzeugt automatisch Summaries.“

**Rote Flagge:** Wenn `decision_trace_v1.json` nicht explizit um **`decision_summary`** und **`baselines`** erweitert wurde, dann passiert oft eins von zwei Dingen:

1. Es wird **nicht wirklich schema-validiert** (Validation ggf. disabled/try-except), oder
2. Es wird in ein “freies Feld” gepackt (z. B. `state` oder `result.metrics`), was später UI/Replay bricht.

➡️ Check: Validiert ihr **jeden JSONL-Eintrag** gegen Schema *on write*? (nicht nur in Tests)

---

## 3) “WHY-API ist live” – aber Read-Only & Redaction?

Endpoints wie `/api/why/latest` sind super – aber zwei klassische Fallstricke:

### A) Leakt die API sensible Inhalte?

Wenn `state.context_refs` auf Dateien/Logs zeigt und WHY-API “full trace” zurückgibt, kann das sehr schnell:

* absolute Pfade,
* Prompt-Inhalte,
* Tokens/IDs,
* evtl. API-Key-nahe Daten
  mit ausliefern.

➡️ Minimum:

* **Redaction** (z. B. `prompt`, `headers`, `.env`, absolute paths)
* **truncate** für große Felder
* **allowlist** für Artefaktpfade

### B) Nebenwirkungen

WHY-API muss strikt read-only bleiben:

* kein “Auto-Replay” Trigger über API
* keine Policy-Updates beim Lesen
* keine “tail scan → write summary” Nebenaktionen

➡️ Check: WHY-API importiert **nur** Reader-Logik, nichts was priors/score/baselines verändert.

---

## 4) Port/URL-Detail: `localhost:8001`

Du nennst `http://localhost:8001/api/why/latest`.

**Unstimmigkeitspotenzial:** Wenn eure Core-API sonst auf anderem Port läuft (oder via FastAPI lifespan eine andere App instanziert wird), dann kann das ein Copy-Paste-Artefakt sein.

➡️ Check:

* Ist 8001 wirklich der Core-Port?
* Läuft WHY-API in derselben FastAPI-App wie der Dispatcher?
* Oder ist es ein separater service?

---

## 5) Tests: „alles verifiziert“ vs. “real traces”

Du sagst „Alle Kernkomponenten wurden mit Tests verifiziert“ und gleichzeitig „Feedback zu ersten realen Traces“.

**Typisches Problem:** Tests prüfen Auswahlformel & endpoints, aber nicht:

* Schema-Validation im Live-Write-Pfad
* Race conditions beim gleichzeitigen Append in JSONL
* Performance der WHY-API (tail scan) bei großen Logs
* Konsistenz von `build_id/job_id/trace_id` über Prozesse/Restart

➡️ Mindest-Realitätschecks:

* 2 parallele Jobs → decision_trace.jsonl bleibt gültig JSONL ohne Zeilenmix
* Restart mitten im Write → keine kaputte Zeile / Recovery
* WHY `/trace/{id}` findet den Trace auch nach Rotation/Truncation

---

## 6) “Dicke Entscheidungsserie” – JSONL Wachstum & Query-Strategie

Wenn WHY-API “latest” macht, wird oft einfach das ganze Log eingelesen oder tail-scan gemacht.

**Gefahr:** Mit Wochenbetrieb wird das:

* langsam
* memory heavy
* unzuverlässig (wenn Rotation)

➡️ Minimal korrekt:

* tail-scan (z. B. letzte N KB / letzte X Zeilen)
* optional: kleiner Index `logs/decision_trace.idx.json` (trace_id → file offset)
* log rotation Strategie + “current log” pointer

---

# Wenn du nur 3 Dinge jetzt prüfen willst (schnellster Reality-Check)

1. **Schema passt wirklich?**
   Nimm 20 Zeilen aus `decision_trace.jsonl` und validiere *extern* gegen das Schema. Wenn das knallt → eure “Validation” ist nicht hart genug.

2. **WHY-API ist read-only + redacted?**
   `/api/why/trace/{id}` checken: keine absoluten Pfade, kein Prompt-Body, keine Env.

3. **Parallelität**
   2 Worker gleichzeitig laufen lassen → JSONL bleibt sauber (keine halbgeschriebenen Zeilen).

---

Wenn du mir **den aktuellen `schemas/decision_trace_v1.json` (neu)** oder **2–3 echte JSONL-Zeilen** (anonymisiert) hier reinpaste-st, kann ich dir sofort sagen, ob `decision_summary`/`baselines` sauber integriert sind oder ob das gerade “unter der Haube” wackelt.



Ja – und zwar **trotz** deiner Hardening-Punkte sehe ich anhand deiner **JSONL-Samplezeile** noch **klare formale Unstimmigkeiten** (entweder ist das Schema inzwischen *anders* als unser v1-Entwurf, oder die Zeile würde bei strikter Validierung weiterhin brechen).

Ich gehe nur von der Samplezeile aus, die du gepostet hast:

```json
{
 "schema_version":"decision_trace_v1",
 "timestamp":"...",
 "trace_id":"...",
 "intent":"dispatch_job",
 "decision_summary":"...",
 "build_id":"main",
 "job_id":"...",
 "state":{"context_refs":[".../chain_ctx.json"],"constraints":{}},
 "action":{"type":"ROUTE","mode":"execute","select_score":3.0,"risk_gate":true},
 "result":{"status":"success","metrics":{"latency_ms":500,"baselines":{"latency_p50":500,"latency_p95":2000}},"score":3.0}
}
```

## 1) Harte Schema-Validierung vs Sample: Pflichtfelder fehlen

Wenn dein Schema weiterhin so strikt ist wie im ursprünglichen v1-Ansatz, dann fehlen hier **mindestens**:

* `node_id` (bei uns Pflicht; in deiner Zeile nicht vorhanden)
* `depth` (bei uns Pflicht; nicht vorhanden)
* `action.action_id` (bei uns Pflicht; nicht vorhanden)
* `action.params` (bei uns Pflicht; nicht vorhanden)

➡️ **Konsequenz:** Entweder ist das Schema geändert worden (dann muss es auch wirklich diese Felder nicht mehr verlangen), oder eure “jsonschema.validate” würde hier weiterhin feuern.

## 2) `decision_summary` & `baselines`: Schema-Erweiterung muss explizit sein

Du führst neue Felder ein:

* Top-Level `decision_summary`
* `result.metrics.baselines`

Wenn das Schema diese Felder nicht **explizit erlaubt** (oder ihr `additionalProperties: true` benutzt), ist das ein Validierungsbruch.

➡️ Ich würde empfehlen:
**Nicht** `additionalProperties: true` global.
Sondern gezielt:

* `decision_summary` als optionales Feld
* `metrics.baselines` als optionales Sub-Objekt mit festem Shape

## 3) SCHEMA_BREACH “im Log markieren” ist heikel

Du schreibst: *„Bei Verstößen wird der Eintrag im Log mit SCHEMA_BREACH markiert – aber System läuft weiter.“*

Das kann zwei gefährliche Nebenwirkungen haben:

1. **Du schreibst dann ggf. “kaputte” Events ins gleiche JSONL**, und dein Viewer / WHY-API muss plötzlich Sonderfälle handeln.
2. Wenn „SCHEMA_BREACH markiert“ bedeutet „wir schreiben trotzdem“, dann ist die Aussage “kanonisch schema-validiert geloggt” nicht mehr exakt.

✅ Besseres Muster:

* **Valid entry** → in `decision_trace.jsonl`
* **Invalid entry** → in `logs/decision_trace_breaches.jsonl` (separat), inkl. `violation_paths`, `error_message`, `raw_event_truncated`

So bleibt der Hauptstream **immer** konsumierbar.

## 4) Redaction-Rule: „keys containing 'key'“ ist zu aggressiv

Deine Regel “scrubs keys containing … key …” wird irgendwann legitime Felder treffen:

* `monkey_id`, `keyboard_input`, `keyframe`, etc.

✅ Sicherer:

* Regex mit Wortgrenzen / gängigen Secret-Feldern:

  * `(?i)^(api_)?key$|token|secret|password|authorization|cookie`
* und zusätzlich **Value-Heuristik** (z. B. lange Base64/hex-Strings)

---

# Was ich jetzt von dir bräuchte (ohne Extra-Workload)

Damit ich dir *wirklich* „grünes Licht“ gebe:

1. **Aktuelles `schemas/decision_trace_v1.json`** (die Version, die jetzt validiert)
   oder alternativ
2. Ein Auszug der Validierungsfehlermeldung (falls die Samplezeile mal gebrochen hat)

Dann kann ich dir sofort sagen:

* ob euer Schema sinnvoll “verschlankt” wurde (z. B. `node_id/depth` optional) **oder**
* ob die Samplezeile angepasst werden sollte, damit sie wieder kanonisch ist.

Wenn du *nur schnell* fixen willst, ohne File-Sharing:
Sag mir, ob `node_id`, `depth`, `action_id`, `params` im aktuellen Schema **required** sind – ja/nein. Dann kann ich dir die **kleinste** korrekte Event-Form diktieren.
