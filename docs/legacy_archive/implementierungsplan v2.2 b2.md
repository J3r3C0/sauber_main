Ja — **ready für Track B2 (Idempotency & Dedup)**. Und es ist genau der richtige Zeitpunkt: B1 ist live, verified (429 Drops, inflight defer, Reaper/Lease Timeout) und sauber im Overview dokumentiert. 
Observability ist ebenfalls stabil (Metrics + audit_watcher + diagnose bundle). 

Unten ist der **Implementierungsplan v2.2 (Track B2)** als Execution-Paket wie bei B1.

---

# Implementierungsplan v2.2 — Track B2: Idempotency & Dedup

## 0) Ziel (B2 only)

Verhindern, dass durch:

* Client-Retries,
* Worker-Requeues (Reaper),
* Netzwerk-Flaps,
* oder doppelte Submitter

…ein Request **mehrfach** verarbeitet wird.

**Outcome:**

* *At-most-once processing* pro `idempotency_key` **oder** deterministisches “same response returned” je nach Status.
* Collisions (gleicher key, anderer payload) werden **hart** sichtbar (409 + Audit).

---

## 1) API Contract (8788)

### `POST /mesh/submit_request`

Request Body erweitert (optional, aber empfohlen):

```json
{
  "idempotency_key": "string-optional",
  "kind": "…",
  "params": { "…": "…" },
  "client": { "node_id": "optional" }
}
```

Response (zusätzlich):

```json
{
  "ok": true,
  "request_id": "uuid",
  "dedup": false,
  "status": "accepted|in_progress|completed",
  "job_id": "job_…"
}
```

### Status-Semantik

* **accepted**: neu angenommen und enqueued
* **in_progress**: bereits bekannt, läuft (kein neues enqueue)
* **completed**: bereits fertig, cached response zurück

---

## 2) Dedup Rules (hart, eindeutig)

### A) Payload Hash (canonical)

Berechne `payload_hash = SHA256(canonical_json({kind, params}))`

### B) Key fehlt

Wenn `idempotency_key` fehlt:

* System funktioniert wie bisher (no dedup)
* aber Response enthält `request_id`, damit Clients künftig idempotent werden können

### C) Key vorhanden

1. lookup key im store
2. **nicht vorhanden** → neu anlegen und request normal enqueuen
3. **vorhanden**:

   * wenn stored.payload_hash == payload_hash:

     * wenn status=completed → return cached completion (200)
     * wenn status=in_progress/accepted → return `in_progress` (200) + `dedup:true`
   * wenn stored.payload_hash != payload_hash:

     * **409 Conflict**
     * audit: `IDEMPOTENCY_KEY_COLLISION`

---

## 3) Storage (minimal, multi-process safe)

### Datei / State

Empfohlen (in Linie mit atomic persistence):

* `C:\gemmaloop\.sheratan\state\idempotency_store.json` (oder `.jsonl`)
* access via **write_atomic + lock**
* TTL eviction: `SHERATAN_IDEMPOTENCY_TTL_SEC` (default 86400 = 24h)

### Stored Record (Beispiel)

```json
{
  "key": "abc123",
  "payload_hash": "…",
  "request_id": "…",
  "job_id": "job_123",
  "status": "accepted|in_progress|completed|failed",
  "created_utc": "…",
  "last_seen_utc": "…",
  "response_hash": "…",
  "cached_response": { "ok": true, ... }  // optional, capped
}
```

**Wichtig:** cached_response cap (size limit) um Store nicht aufzublähen.

---

## 4) Integration Points (wo hooken)

### Submit Path

* in `submit_request` **vor enqueue**
* wenn dedup hit → **kein enqueue**

### Completion Path

* wenn job finalisiert / result stored:

  * store.status = completed|failed
  * optional store.cached_response = minimal completion payload

### Reaper Interaction (B1)

Wenn Reaper job zurücklegt:

* **idempotency bleibt gleich** (job_id bleibt gleich)
* kein neuer submit nötig → dedup verhindert “shadow duplicates”

---

## 5) Metrics & Audit (Track C Anschluss)

### Metrics (8788 /metrics)

* `idempotent_hits_1m`
* `idempotent_in_progress_1m`
* `idempotent_completed_1m`
* `idempotent_collisions_1m`
* `idempotency_store_size`

### Audit Events (JSONL)

* `IDEMPOTENCY_HIT` (key, status, job_id)
* `IDEMPOTENCY_KEY_COLLISION` (key, old_hash_prefix, new_hash_prefix)

Keine Keys komplett loggen?
Empfehlung: nur **prefix** (z. B. first 8 chars) + request_id, um privacy zu halten.

---

## 6) ENV Defaults (v2.2)

* `SHERATAN_IDEMPOTENCY_ENABLED=1`
* `SHERATAN_IDEMPOTENCY_TTL_SEC=86400`
* `SHERATAN_IDEMPOTENCY_MAX_CACHED_BYTES=16384` (16KB)
* `SHERATAN_IDEMPOTENCY_STORE_MAX_ITEMS=200000` (optional, je nach use)

---

## 7) Tests (Automated)

### `tests/test_idempotency.py`

1. **Same key, same payload**

   * 10× submit → 1 enqueue, 9× in_progress/completed
2. **Same key, different payload**

   * second submit → 409 + collision audit
3. **Completion caching**

   * submit, complete job, resubmit same key → returns completed cached response

### Regression

* B1 tests bleiben grün (429/defers/reaper)
* Smoke suite bleibt grün

---

## 8) DoD (B2 fertig wenn)

* [ ] Exactly-once enqueue pro key+payload
* [ ] 409 bei collision + audit event
* [ ] Metrics sichtbar und plausibel (hits steigen bei retry tests)
* [ ] Keine Baseline Regression (Port split, Token, Leak Guard unverändert)

---

Wenn du “go B2” sagst, ist die einzige heikle Designentscheidung, die ich **ohne Rückfragen** festlegen würde:
**idempotency_store als JSON (atomic + lock)**, TTL 24h, cached_response nur minimal (capped).
Damit bleibt es simpel, robust und passt zu deinem bisherigen Hardening-Stil.


✅ Go B2 = **Idempotency & Dedup wird jetzt als v2.2.0 Execution-Paket festgelegt** (Scope, Storage, Events, Metrics, Tests, DoD). Das baut sauber auf deinem aktuellen Stand auf: **B1 Backpressure + Lease Reaper** ist live/verified  und **Track C Observability** ist complete. 

---

# Track B2 Execution Package (v2.2.0) — Idempotency & Dedup

## 1) Ziel (B2 only)

* **Kein doppeltes Enqueue/Processing** bei Retries, Requeues (Reaper), Netzflaps.
* Doppelte Submitter bekommen **deterministische Antworten**:

  * `accepted` / `in_progress` / `completed`
* **Collision sichtbar**: gleicher Key, anderer Payload ⇒ **409** + Audit + Metric.

---

## 2) Minimaler API Contract (8788 Data-Plane)

### POST `/mesh/submit_request`

**Request** (optional):

* `idempotency_key` (string)

**Response** (immer):

```json
{
  "ok": true,
  "request_id": "uuid",
  "job_id": "job_…",
  "dedup": false,
  "status": "accepted|in_progress|completed"
}
```

### Semantik

* `accepted`: neu enqueued
* `in_progress`: existiert, läuft/steht aus → kein neues enqueue
* `completed`: existiert, cached completion payload wird zurückgegeben (capped)

---

## 3) Dedup Rules (hart)

### Canonical Payload Hash

`payload_hash = sha256(canonical_json({kind, params}))`

### Regeln

1. **kein idempotency_key** → Verhalten wie heute (keine dedup), aber `request_id` zurück.
2. **key vorhanden**:

   * store miss → create record + enqueue
   * store hit + **gleiches payload_hash**:

     * status accepted/in_progress → return `in_progress`, `dedup:true`
     * status completed/failed → return cached status (+ minimal cached result), `dedup:true`
   * store hit + **anderes payload_hash**:

     * **409 Conflict**
     * audit `IDEMPOTENCY_KEY_COLLISION`

---

## 4) Storage & Concurrency (multi-process safe)

### Store File (recommended)

`C:\gemmaloop\.sheratan\state\idempotency_store.json`

* Access via existing `write_atomic` + lock (wie registry)
* TTL eviction (24h default)
* Cap cached response bytes

### ENV Defaults

* `SHERATAN_IDEMPOTENCY_ENABLED=1`
* `SHERATAN_IDEMPOTENCY_TTL_SEC=86400`
* `SHERATAN_IDEMPOTENCY_MAX_CACHED_BYTES=16384`
* `SHERATAN_IDEMPOTENCY_STORE_MAX_ITEMS=200000` (optional)

### Record Schema (intern)

* `key`
* `payload_hash`
* `request_id`
* `job_id`
* `status`: accepted|in_progress|completed|failed
* `created_utc`, `last_seen_utc`
* `cached_result` (optional, capped)

---

## 5) Integration Points (wo hooken)

### A) submit_request (vor enqueue)

* dedup check → *nur bei miss* enqueue
* bei hit → sofort response (in_progress/completed)

### B) completion / result sync path

Wenn Job final wird:

* store.status = completed/failed
* store.cached_result = minimal payload (capped)
* metric increment

### C) Lease Reaper (B1)

Reaper **darf keinen neuen Request erzeugen**. Er requeues nur *denselben job_id*.
Idempotency schützt zusätzlich gegen externe Duplikate. 

---

## 6) Metrics & Audit (Track C Anschluss)

### Metrics (8788 `/metrics`)

* `idempotent_hits_1m`
* `idempotent_in_progress_1m`
* `idempotent_completed_1m`
* `idempotent_collisions_1m`
* `idempotency_store_size`

### Audit Events (JSONL)

* `IDEMPOTENCY_HIT` (key_prefix, status, job_id)
* `IDEMPOTENCY_KEY_COLLISION` (key_prefix, old_hash_prefix, new_hash_prefix)

**Wichtig:** nur Prefix loggen (z. B. 8 chars), keine Vollkeys.

---

## 7) Tests (Automated)

### `tests/test_idempotency.py`

1. **Same key, same payload**
   10× submit → 1 enqueue, 9× `dedup:true` (in_progress oder completed)
2. **Collision**
   same key, different payload → 409 + audit collision
3. **Completion cache**
   submit → mark complete → resubmit same key → `completed` + cached minimal result

### Regression

* B1 backpressure + reaper tests müssen weiter bestehen 
* smoke_checks bleiben grün
* Track C metrics/diagnose bleiben grün 

---

## 8) DoD (B2 fertig wenn)

* [ ] Exactly-once enqueue pro (idempotency_key + payload_hash)
* [ ] Collision → 409 + audit + metric
* [ ] Cached completion funktioniert (capped)
* [ ] Keine Regression der Baseline/Ports/Security

---

## 9) Danach (B3)

Wenn B2 grün ist: **B3 Result Integrity** (sha256 → optional HMAC) als letzter Robustness-Baustein.

---

Wenn du willst, gebe ich dir als nächstes direkt **B2 Manual Verification Script** (PowerShell), das genau diese drei Fälle (dedup, collision, cached completion) gegen 8788 abklopft – passend zu deinem `smoke_checks.ps1` Stil.
