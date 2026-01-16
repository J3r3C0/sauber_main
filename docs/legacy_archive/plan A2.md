✅ Ja — **ready für Track A2 (Node Attestation)**. Dein Overview zeigt jetzt sauber Track A1 inkl. Dual-Token, Promotion, Audit-Events und die neuen Rollout-Metriken. 

Unten ist **Implementierungsplan v2.5 (Track A2)** als ausführbares Paket, im gleichen Stil wie B1–B3/A1.

---

# Implementierungsplan v2.5 — Track A2: Node Attestation (Drift & Spoof Signals)

## 0) Ziel (A2 only)

**Heartbeats bekommen ein Attestation-Signal**, das der Hub speichert und auswertet, um:

* **Konfig-Drift** (Capabilities/Build geändert) zu erkennen
* **Spoofing-Indikatoren** sichtbar zu machen (gleicher node_id, anderer Fingerprint)
* ohne Hard-Block: **Signal → Health YELLOW + Audit + Metrics**

> A2 ist bewusst “soft enforcement” (Signal first). Hard Policies kommen optional in A3.

---

## 1) Attestation Payload (Heartbeat Erweiterung)

### Heartbeat Request (8787)

Node sendet zusätzlich:

```json
{
  "node_id": "NODE_WORK_B",
  "health": "GREEN",
  "ts_utc": "2026-01-15T22:10:00Z",

  "attestation": {
    "schema": "attestation_v1",
    "build_id": "hub-worker-2026.01.15",
    "capability_hash": "sha256hex...",
    "runtime": {
      "os": "windows|linux",
      "python": "3.11.7"
    }
  }
}
```

### capability_hash (Definition)

Hash über eine **stabile, sortierte** Liste der Node-Fähigkeiten:

Beispiel canonical list:

* `["heartbeat","pull_requests","submit_results","gpu:false","model:llama_cpp"]`

`capability_hash = sha256(canonical_json(capabilities_list))`

> Kein Geheimnis. Nur Drift-Signal.

---

## 2) Hub-Seite: Registry Erweiterung & Drift-Logik

### Storage pro Node (in registry state)

Erweitere Registry record:

* `attestation_first_seen`: { build_id, capability_hash, runtime_summary, ts }
* `attestation_last_seen`: { build_id, capability_hash, ts }
* `attestation_status`: `OK | DRIFT | SPOOF_SUSPECT`

### Regeln (entscheidend, minimal & robust)

**R1: First Seen**

* Wenn Node neu: setze `first_seen = current`

**R2: Drift**

* Wenn `capability_hash` ODER `build_id` sich ändert gegenüber first_seen:

  * setze `attestation_status = DRIFT`
  * setze node health: **YELLOW** (nicht DEAD)
  * audit: `ATTESTATION_DRIFT`

**R3: Spoof Suspect**

* Wenn Node mit gleichem `node_id` in kurzer Zeit mehrfach unterschiedliche attestation sendet (z. B. wechselnde runtime/os) *oder* ein “flip-flop” pattern:

  * `attestation_status = SPOOF_SUSPECT`
  * audit: `ATTESTATION_SPOOF_SUSPECT`
  * optional: markiere YELLOW + erhöhe severity counter

> Keine IP-basierte Blockade in A2 (nur Signal). IP kann aber ins Audit.

---

## 3) Audit Events (JSONL)

* `ATTESTATION_FIRST_SEEN`
* `ATTESTATION_DRIFT`
* `ATTESTATION_SPOOF_SUSPECT`

Fields (sanitized):

* node_id
* old_build_prefix / new_build_prefix (oder voll, wenn unkritisch)
* old_cap_prefix / new_cap_prefix (8 chars)
* remote_addr
* ts_utc

---

## 4) Metrics (8787 /metrics)

Neue counters/gauges:

* `attestation_ok`
* `attestation_drift`
* `attestation_spoof_suspect`
* `attestation_drift_1m`
* `attestation_spoof_1m`

Ziel: Ops sieht sofort “drift happening” beim Deploy.

---

## 5) Backward Compatibility

Wenn ein Node **noch keine attestation** sendet:

* Hub setzt `attestation_status = MISSING`
* health bleibt wie bisher (nicht bestrafen)
* optional metric: `attestation_missing`

So kannst du Nodes schrittweise migrieren.

---

## 6) Files (minimal changes)

### Hub

* `hub/attestation.py` (neu)

  * canonicalize capabilities
  * compute capability_hash (optional helper)
  * evaluate drift/spoof rules
* `hub/registry.py` (erweitern)

  * attestation fields speichern (atomic write bleibt via hub/state.py)
* `hub/serve_gateway.py` / control router

  * im heartbeat handler: `attestation.evaluate_and_update(node_record, payload, remote_addr)`
* `hub/metrics.py`

  * neue attestation metrics
* `hub/audit.py` (oder vorhandenes logging)

  * neue events

### Clients (Sauber Host / Worker)

* `heartbeat.py` (oder jeweiliger client)

  * attestation block ergänzen
  * capabilities list definieren (stabil, sortiert)

---

## 7) Tests (Automated)

### `tests/test_attestation.py`

1. **First seen**

   * heartbeat mit attestation → `ATTESTATION_FIRST_SEEN`, status OK
2. **Drift**

   * gleicher node_id, anderer capability_hash → status DRIFT, health YELLOW
3. **Spoof suspect**

   * flip-flop zwischen zwei hashes in kurzer Zeit → SPOOF_SUSPECT
4. **Missing attestation**

   * heartbeat ohne attestation → MISSING, keine Regression

---

## 8) Manual Verification (Operator)

1. Starte Worker A mit capabilities set X → OK
2. Deploy Worker A mit capabilities set Y → DRIFT + audit + metrics
3. Simuliere “spoof” (node_id gleich, runtime/os anders) → SPOOF_SUSPECT

---

## 9) DoD (A2 abgeschlossen wenn)

* [ ] Hub speichert attestation per node
* [ ] Drift → YELLOW + audit + metrics
* [ ] Spoof suspect → audit + metrics
* [ ] Missing attestation ist kompatibel (kein Hard-Fail)
* [ ] Smoke suite bleibt grün, Port/Token/Leak-Guard unverändert 

---

## Entscheidungspunkt nach A2

Danach kannst du wählen:

* **A3 Policy Enforcement** (Hard rules: block SPOOF_SUSPECT / require attestation for certain zones)
* oder **Attestation Signatures** (echte Kryptografie; braucht Keying/rotation → nur wenn du’s wirklich willst)

Wenn du “go A2” sagst, ist die einzige Festlegung, die ich ohne Rückfragen treffe:
**Attestation bleibt “signal-only” (YELLOW), kein Block**, damit Deployments nicht plötzlich sterben.

✅ Go A2. Hier ist das **Execution-Paket v2.5.0 — Node Attestation** (drift/spoof signals), so dass du es 1:1 umsetzen und verifizieren kannst, ohne die Baseline (Ports/Token/Leak-Guard) zu gefährden. 

---

# Track A2 Execution Package (v2.5.0) — Node Attestation

## 1) Ziel (A2 only)

* Hub erkennt **Drift** (build/capabilities ändern sich) und **Spoof-Suspects** (flip-flop / widersprüchliche Attestation).
* Reaktion: **Signal-only** → Health **YELLOW**, Audit-Event, Metrics.
* Backward compatible: Nodes ohne Attestation bleiben lauffähig.

---

## 2) Heartbeat Contract (8787 /api/hosts/heartbeat alias oder canonical)

### Request payload (additive)

```json
{
  "node_id": "node-A",
  "health": "GREEN",
  "ts_utc": "2026-01-15T23:10:00Z",
  "attestation": {
    "schema": "attestation_v1",
    "build_id": "core-2026.01.15",
    "capability_hash": "sha256hex...",
    "runtime": {
      "os": "windows",
      "python": "3.11.7"
    }
  }
}
```

### capability_hash Definition (client-side)

`capability_hash = sha256(canonical_json(sorted(capabilities_list)))`

Beispiel capabilities_list:

```json
[
  "heartbeat",
  "pull_requests",
  "submit_results",
  "zone:worker",
  "gpu:false",
  "model:llama_cpp"
]
```

---

## 3) Registry Erweiterung (per node record)

Neuer Block in `nodes_registry.json` (oder wie deine Datei heißt):

```json
{
  "attestation": {
    "first_seen": {
      "ts_utc": "...",
      "build_id": "...",
      "capability_hash": "...",
      "runtime": { "os": "...", "python": "..." }
    },
    "last_seen": {
      "ts_utc": "...",
      "build_id": "...",
      "capability_hash": "..."
    },
    "status": "OK|DRIFT|SPOOF_SUSPECT|MISSING",
    "drift_count": 0,
    "spoof_count": 0,
    "last_change_utc": null
  }
}
```

Persistence bleibt über deine zentrale atomic write (hub/state.py).

---

## 4) Regeln (minimal, robust)

### R0: Missing Attestation

* Wenn `attestation` fehlt:

  * `status = MISSING`
  * **keine** Health-Strafe
  * metrics: `attestation_missing += 1`

### R1: First Seen

* Wenn `first_seen` noch nicht existiert:

  * setze `first_seen = current`
  * `status = OK`
  * audit: `ATTESTATION_FIRST_SEEN`

### R2: Drift

* Wenn `build_id` oder `capability_hash` ≠ `first_seen.*`:

  * `status = DRIFT`
  * `drift_count += 1`
  * setze node `health` auf **YELLOW** (nur wenn nicht already worse)
  * audit: `ATTESTATION_DRIFT`

> Drift ist normal bei Deploys — daher **signal only**.

### R3: Spoof Suspect (Flip-Flop)

* Wenn innerhalb eines kurzen Fensters (z. B. 120s) mehrfach wechselnde `capability_hash` eintreffen (A→B→A oder A→B→C):

  * `status = SPOOF_SUSPECT`
  * `spoof_count += 1`
  * audit: `ATTESTATION_SPOOF_SUSPECT`
  * node health bleibt **YELLOW** (kein Block in A2)

**Empfohlene ENV Defaults**

* `SHERATAN_ATTESTATION_FLIP_WINDOW_SEC=120`
* `SHERATAN_ATTESTATION_FLIP_THRESHOLD=3`

---

## 5) Audit Events (JSONL)

* `ATTESTATION_FIRST_SEEN`
* `ATTESTATION_DRIFT`
* `ATTESTATION_SPOOF_SUSPECT`

Sanitized fields:

* `node_id`
* `old_cap_prefix`, `new_cap_prefix` (8 chars)
* `old_build`, `new_build` (oder prefix)
* `remote_addr`
* `ts_utc`

---

## 6) Metrics (8787 /metrics)

Add:

* `attestation_ok`
* `attestation_missing`
* `attestation_drift`
* `attestation_spoof_suspect`
* `attestation_drift_1m`
* `attestation_spoof_1m`

Damit siehst du Deploy-Wellen und Spoof-Verdacht sofort.

---

## 7) Code-Module (File Plan)

### Hub

* `hub/attestation.py` (neu)

  * `compute_capability_hash(caps: list[str])`
  * `evaluate(node_record, attestation, now_utc) -> (status, events, health_hint)`
  * `detect_flipflop(history, window, threshold)`
* `hub/registry.py` (update record + persist)
* `hub/serve_gateway.py` (heartbeat handler calls attestation.evaluate)
* `hub/metrics.py` (new counters/gauges)
* `hub/audit.py` (event writers)

### Clients

* `heartbeat.py` / `mesh_client.py`

  * stable capabilities list
  * attach attestation block

---

## 8) Tests (Automated)

### `tests/test_attestation.py`

1. First seen ⇒ status OK + audit
2. Drift ⇒ status DRIFT + health YELLOW + metrics increment
3. Missing ⇒ status MISSING, no penalty
4. Flip-flop ⇒ SPOOF_SUSPECT after threshold

---

## 9) Manual Verification (Operator)

1. **Normal**

* Node heartbeat with fixed caps/build → OK

2. **Drift**

* Change build_id OR caps → DRIFT + YELLOW + audit

3. **Spoof suspect**

* Send 3 heartbeats alternating caps hashes within 120s → SPOOF_SUSPECT

---

## 10) DoD (A2 done when)

* [ ] Registry speichert attestation fields persistent
* [ ] Drift/Spoof erzeugen Audit + Metrics
* [ ] Missing ist kompatibel
* [ ] Keine Baseline Regression (Tokens/Ports/Leak-Guard/Smoke) 

---

Wenn du willst, kann ich dir direkt als nächstes ein **A2 verify.ps1** geben (wie bei B2/B3), das genau die drei Fälle (first_seen, drift, flip-flop) gegen 8787 automatisiert testet.
