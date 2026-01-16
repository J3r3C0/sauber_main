Ja — **bereit für Track B (Data-Plane Robustness)**. Track C ist sauber abgeschlossen (Metrics auf beiden Ports, Audit-Watcher mit verifiziertem `BURST_AUTH_FAILURE`, Diagnose-Bundle, Doku/Keys im Overview). 

Unten ist der **Implementierungsplan v2.1 (Track B)** in der gleichen Form: Backpressure → Idempotency/Dedup → Result Integrity. Reihenfolge ist absichtlich so gewählt (erst Lastkontrolle, dann Duplicate-Kontrolle, dann Integrität).

---

# Implementierungsplan v2.1 — Track B: Data-Plane Robustness

## Zielbild

* Data-Plane (8788) bleibt **resilient unter Last**, ohne dass Control-Plane (8787) betroffen ist.
* Doppelte Requests führen nicht zu Doppel-Ausführung.
* Results sind manipulationssicher (mindestens checksum, optional HMAC).
* Alles messbar über `/metrics` (Track C) und auditiert über JSONL.

---

## B0. Constraints (Baseline Guardrails)

* **Keine Änderungen** an:

  * Port Split + Leak Guard (410) + Token Enforcement (v1.5) 
  * Observability (v2.0) bleibt read-only und stabil 
* Track B darf **nur 8788 Data-Plane** betreffen (Control bleibt unberührt).

---

## B1. Backpressure + Retry Budgets (First)

### Scope

Einführen von harten Grenzen und kontrolliertem Degrading:

* Queue Depth Limit (global + optional per-node)
* Inflight Limit (Leases)
* Retry Budgets + Backoff
* Minimal DLQ (Dead-letter light)

### Verhalten (konkret)

* `submit_request`:

  * Wenn `queue_depth >= MAX_QUEUE_DEPTH` → **429 Too Many Requests** (oder 503) + audit event `BACKPRESSURE_DROP`
* `pull_requests`:

  * Wenn `inflight >= MAX_INFLIGHT` → empty / defer (kein busy loop)
* Retry:

  * `max_attempts` (z. B. 5)
  * exponential backoff (z. B. 1s,2s,4s,8s,… capped)
  * budget pro job: `retry_budget_sec` oder `retry_budget_attempts`

### Konfiguration (ENV)

* `SHERATAN_MAX_QUEUE_DEPTH=500` (start konservativ)
* `SHERATAN_MAX_INFLIGHT=50`
* `SHERATAN_RETRY_MAX_ATTEMPTS=5`
* `SHERATAN_RETRY_BACKOFF_BASE_MS=500`
* `SHERATAN_RETRY_BACKOFF_CAP_MS=15000`
* optional: `SHERATAN_DLQ_ENABLED=1`

### Files

* `hub/queue_store.py` (oder Erweiterung bestehender queue storage)
* `hub/data_plane.py` (8788 router / endpoints)
* `hub/retry_policy.py`
* `hub/dlq.py` (optional light)
* `hub/metrics.py` erweitern (queue_depth, inflight, drop_count_1m)

### DoD

* Unter synthetischer Last:

  * Hub bleibt responsiv
  * 429/503 passieren kontrolliert
  * `/metrics` zeigt drop/throttle counts
* Keine Registry-/Control-Plane Regression
* Smoke bleibt grün

---

## B2. Idempotency + Dedup (Second)

### Scope

Verhindern von Doppel-Ausführung bei retries / client reconnects / duplicates.

### Datenmodell

* Request nimmt `idempotency_key` optional an (string)
* Wenn nicht vorhanden:

  * server generiert `request_id` (uuid) **und gibt ihn zurück**
  * Clients können später idempotent werden

### Storage

* `idempotency_store` (TTL-based, z. B. 24h):

  * key → {status, request_id, job_id, created_at, last_seen, response_hash}
* dedup rule:

  * gleicher key + identischer payload-hash → return cached response (200)
  * gleicher key + anderer payload-hash → 409 Conflict + audit `IDEMPOTENCY_KEY_COLLISION`

### Files

* `hub/idempotency.py`
* `hub/data_plane.py` (hook in submit endpoint)
* `hub/metrics.py` (idempotent_hits_1m, collisions_1m)

### DoD

* 10× submit identischer job mit gleichem idempotency_key:

  * exactly once processing
  * 10 responses consistent
* Collision case test (same key, different payload) returns 409 + audit

---

## B3. Result Integrity (Third)

### Scope

Sicherstellen, dass results nicht “still” manipuliert werden.

### Level 1 (Minimum)

* canonical JSON serialization of result payload
* `result_sha256` = SHA256(canonical_json)
* hub verifies checksum on `sync_results` (oder result submit)

### Level 2 (Optional, empfohlen)

* HMAC sign:

  * `result_sig = HMAC_SHA256(SHERATAN_HUB_TOKEN or SHERATAN_RESULT_HMAC_KEY, canonical_json)`
* verify signature server-side
* audit event on mismatch: `RESULT_INTEGRITY_FAIL`

### ENV

* `SHERATAN_RESULT_INTEGRITY=sha256|hmac` (default sha256)
* optional: `SHERATAN_RESULT_HMAC_KEY=...` (wenn nicht hub token verwenden willst)

### Files

* `hub/result_integrity.py`
* `hub/data_plane.py` (verification on result ingestion)
* `hub/metrics.py` (integrity_fail_1m)

### DoD

* Valid result accepted
* Tampered result rejected + audit event + metric increment

---

## Tests (Automated)

### New

* `tests/test_backpressure.py`
* `tests/test_idempotency.py`
* `tests/test_result_integrity.py`

### Must keep

* `.\smoke_checks.ps1` stays green
* existing Track C checks remain valid

---

## Manual Verification Script (Operator-level)

1. Normal traffic → no drops
2. Load test (burst submits) → controlled 429/503 + metrics reflect it
3. Duplicate submit with idempotency_key → dedup hit
4. Tamper result payload → integrity fail + audit log entry

---

## Deliverables

* Code modules (B1–B3)
* Updated `system_overview.md`:

  * neue ENV vars
  * failure modes (“BACKPRESSURE_DROP”, “IDEMPOTENCY_COLLISION”, “RESULT_INTEGRITY_FAIL”)
* Walkthrough update (Track B verification)

---

Wenn du “go” sagst, ist der **erste Schritt in Track B** immer **B1 (Backpressure)**.
Das ist die Basis, damit Idempotency/Integrity nicht unter Last an den falschen Stellen “explodieren”.


✅ Go = **Track B1 (Backpressure + Retry Budgets)** wird jetzt als **konkretes Execution-Paket** festgezurrt – mit **Patch-Scope, exakten ENV-Defaults, Endpoint-Verhalten, Tests und DoD**. Track C ist sauber als Voraussetzung belegt (Metrics/Watcher/Diagnostics live). 

---

# Track B1 Execution Package (v2.1.0) — Backpressure + Retry Budgets

## 1) Ziel (B1 only)

* **8788 Data-Plane** bleibt stabil unter Burst/Last.
* Kontrolliertes Degrading: **429/503 statt Crash/Timeout-Spirale**.
* Metrics zeigen Drops/Throttles.
* Audit loggt Backpressure Events (ohne Secrets).

> Keine Änderungen an 8787 Control-Plane / Baseline Split / Leak-Guard / Token.

---

## 2) Konfig (ENV Defaults)

### Hard Limits

* `SHERATAN_MAX_QUEUE_DEPTH=500`
* `SHERATAN_MAX_INFLIGHT=50`
* `SHERATAN_QUEUE_ITEM_TTL_SEC=3600` (optional, für stale queue items)

### Retry Policy

* `SHERATAN_RETRY_MAX_ATTEMPTS=5`
* `SHERATAN_RETRY_BACKOFF_BASE_MS=500`
* `SHERATAN_RETRY_BACKOFF_CAP_MS=15000`

### Behavior Toggles

* `SHERATAN_BACKPRESSURE_MODE=429`  *(oder 503, wenn du “service busy” bevorzugst)*
* `SHERATAN_DLQ_ENABLED=1`
* `SHERATAN_DLQ_MAX_ITEMS=1000`

---

## 3) Endpoint-Verhalten (8788 Data)

### A) `POST /mesh/submit_request`

**Pre-checks (in dieser Reihenfolge):**

1. Auth ok (bestehend)
2. Payload validation (bestehend)
3. **Backpressure gate**

   * Wenn `queue_depth >= MAX_QUEUE_DEPTH`:

     * return `429 Too Many Requests` (oder 503) mit:

       ```json
       {"ok": false, "error": "backpressure", "queue_depth": 500, "max": 500}
       ```
     * audit event: `BACKPRESSURE_DROP`
     * metric increments: `queue_drop_1m`, `backpressure_active=1`

**Wenn ok:** request wird normal enqueued.

### B) `POST /mesh/pull_requests`

**Inflight gate**

* Wenn `inflight >= MAX_INFLIGHT`:

  * return `{"ok": true, "jobs": [], "defer_ms": 500}`
  * metric: `inflight_saturated_1m`

*(Wichtig: kein hartes 429 für pull – sonst Worker busy-loopen und erzeugen Last.)*

### C) Result ingestion (falls vorhanden)

* Optional: limit outstanding results (später B3 verstärkt)

---

## 4) Queue/Inflight Datenmodell (minimal)

### queue store (existing oder neu)

* `queue_depth` = len(pending)
* `inflight` = leases active (by job_id + lease_until)
* Leases: `lease_until = now + lease_sec`
* Reaper: expired leases zurück zu pending (oder mark retry)

### Retry budgets

* pro job: `attempts`, `first_seen`, `last_error`
* wenn attempts > MAX → DLQ (wenn enabled), sonst “failed” + audit

---

## 5) Metrics Erweiterung (Track C Anschluss)

Auf **8788 `/metrics`** ergänzen:

* `queue_depth`
* `inflight`
* `queue_drop_1m`
* `inflight_saturated_1m`
* `retry_scheduled_1m`
* `dlq_size`

Auf **8787** unverändert.

---

## 6) Audit Events (JSONL)

Neue Events im `hub_security_audit.jsonl` (oder eigenes ops audit, aber konsistent):

* `BACKPRESSURE_DROP` (fields: ts, queue_depth, max, path, remote_addr)
* `INFLIGHT_SATURATED` (fields: inflight, max)
* `DLQ_ENQUEUE` (job_id, reason, attempts)

No tokens. Kein body dump.

---

## 7) Tests (Automated)

### `tests/test_backpressure.py`

1. Fill queue bis `MAX_QUEUE_DEPTH`
2. submit_request +1 → expect 429/503 + audit line exists
3. inflight künstlich auf `MAX_INFLIGHT` → pull_requests returns empty + defer_ms

### `tests/test_retry_budget.py`

* job fails repeatedly → attempts increments → DLQ after MAX_ATTEMPTS

> Smoke suite muss weiter grün sein (v1.5 + v2.0).

---

## 8) Manual Verification (Operator)

**A) Quick**

```powershell
.\smoke_checks.ps1
Invoke-RestMethod http://localhost:8788/metrics
```

**B) Burst**

* 600 submits in kurzer Zeit (oder scripted)
* Erwartung:

  * ab Limit: 429/503
  * metrics zeigen drop rate
  * audit enthält BACKPRESSURE_DROP

---

## 9) DoD (Definition of Done)

* [ ] Unter Burst keine timeouts/500-Spirale, stattdessen kontrollierte 429/503
* [ ] `/metrics` zeigt drop/throttle/retry counters
* [ ] Audit log enthält Events ohne Secrets
* [ ] Keine Änderung an 8787 behavior
* [ ] Smoke suite bleibt grün

---

## 10) Nächster Schritt nach B1

Wenn B1 “Green” ist, geht’s automatisch zu:

* **B2 (Idempotency/Dedup)** → verhindert Doppel-Ausführung bei Retries/Resends
* danach **B3 (Result Integrity)**

---

Wenn du mir jetzt einfach **den Repo-Pfad/Dateinamen** nennst, wo aktuell die 8788 endpoints implementiert sind (z. B. `hub/serve_gateway.py` vs `hub/data_plane.py`), kann ich dir den **minimalen Patch-Ort** als “edit list” in 10 Zeilen geben (welche Funktionen, welche checks, welche counters).
