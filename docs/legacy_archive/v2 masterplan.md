Alles – **in der korrekten Reihenfolge**, so dass du die v1.5-Baseline **nicht** gefährdest und jede Stufe messbar „done“ ist.

> Baseline ist gefroren (v1.5) und compliant. 
> Runbook/Ports/ENV/Smoke sind dokumentiert und repeatable.

---

## Reihenfolge (warum genau so)

1. **Track C (Observability V2)** zuerst:
   gibt dir Telemetrie + Alarme, bevor du Verhalten/Last veränderst. Minimales Risiko, maximaler Nutzen.

2. **Track B (Data-Plane V2)** danach:
   hier entstehen reale Failure-Modes (Backpressure, Retries, Dedup). Mit Observability davor siehst du sofort, ob du dich verschlechterst.

3. **Track A (Control-Plane V2 / Governance)** zuletzt:
   Policy/Rotation/Attestation sind „sharp tools“. Wenn Data-Plane stabil und messbar ist, kannst du Governance sauber draufsetzen.

---

# V2 Masterplan (C → B → A)

## Track C — Observability V2 (1. Schritt)

### C1. Metrics Endpoint (read-only)

**Ziel:** Ein minimaler `/metrics` oder `/api/metrics` pro Plane:

* counts: ONLINE/STALE/DEAD
* auth_fail rate (rolling window)
* port_mismatch rate
* queue depth (nur 8788)

**DoD**

* smoke_checks erweitert: “metrics reachable”
* keine Secrets/PII in metrics

### C2. Audit Watcher (Alert Hook)

**Ziel:** watcher auf `hub_security_audit.jsonl`:

* Burst Detection: AUTH_FAILURE > N / min
* PORT_MISMATCH > N / min
* Optional: schreibt `alerts.jsonl` + console summary

**DoD**

* simulierte Fehlversuche → Alert triggert
* false-positive budget (z. B. ignore localhost)

### C3. One-Command “diagnose bundle”

**Ziel:** `diagnose.ps1` (oder CLI):

* sammelt: health, registry snapshot, last 200 audit lines, last 200 hub logs
* packt in `diag_bundle_<timestamp>.zip`

**DoD**

* läuft offline
* enthält keine Tokens

---

## Track B — Data-Plane V2 (2. Schritt)

### B1. Backpressure + Budgets

**Ziel:** harte Grenzen:

* max queue depth / per-node leases
* retry budgets (max attempts, exponential backoff)
* drop/park rules (DLQ-light)

**DoD**

* künstlich Last erzeugen → system degradiert kontrolliert, nicht chaotisch
* metrics zeigen throttling statt crash

### B2. Idempotency + Dedup

**Ziel:** doppelte submits werden “latest wins” oder “same idempotency key → same result”.

* `idempotency_key` im submit_request
* server-side dedup store (klein, TTL-basiert)

**DoD**

* 10× submit gleicher job → 1 processing, 10 identical responses

### B3. Result Integrity (light)

**Ziel:** result checksum / signature:

* mindestens SHA256 über canonical result payload
* optional HMAC (mit plane token oder extra key)

**DoD**

* manipulierter result → reject + audit event

---

## Track A — Control-Plane V2 / Governance (3. Schritt)

### A1. Policy Registry (versioned)

**Ziel:** Regeln als “immutable policy snapshots”:

* allow/deny per zone + capability
* risk gates (z. B. block admin ops unless local)
* policy version pinned im registry state

**DoD**

* policy version sichtbar in `/api/registry`
* Änderung = neue Version, keine silent edits

### A2. Token Rotation (no downtime)

**Ziel:** dual-token window:

* `ACTIVE_TOKEN`, `NEXT_TOKEN`, `ROTATION_UNTIL`
* accept both within window, danach drop old

**DoD**

* Rotation test: clients wechseln token ohne downtime
* audit logs zeigen “old token accepted in rotation window”

### A3. Node Attestation (light)

**Ziel:** anti-spoofing:

* node sends `capability_hash` + `build_id`
* hub stores and flags unexpected changes (“cap drift”)

**DoD**

* mismatch → node marked YELLOW + audit event (nicht sofort DEAD)

---

# Dateistruktur (V2-ready, baseline-sicher)

Empfehlung: **keine großen Umbauten**, nur neue Module:

```
hub/
  metrics.py
  audit_watcher.py
  policies/
    policy_v1.json
    policy_v2.json
  security/
    token_rotation.py
    attestation.py
scripts/
  diagnose.ps1
  load_test.ps1
tests/
  test_metrics.py
  test_backpressure.py
  test_idempotency.py
  test_rotation.py
```

---

# V2 Gatekeeping (damit v1.5 nie bricht)

Für jede Stufe:

* ✅ `.\smoke_checks.ps1` muss grün bleiben
* ✅ Keine Änderung an 8787/8788 Baseline-Regeln (Leak-Guard/Token/atomic) 
* ✅ Runbook erweitern, nicht ersetzen 

---

Wenn du willst, gebe ich dir als nächsten Output **genau einen** Track als „Implementierungsplan v2.x“ im Sheratan-Stil (Tasks, Files, DoD, Tests).
Nach obiger Reihenfolge wäre das: **Track C (Observability V2)** als erstes.
