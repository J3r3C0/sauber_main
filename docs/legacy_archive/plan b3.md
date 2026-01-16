Mission accepted. **B2 ist sauber abgeschlossen** – inhaltlich wie handwerklich.
Das Refactoring (`write_atomic` zentral in `hub/state.py`) ist genau die richtige Entscheidung und stärkt die Konsistenz der gesamten Hub-Persistenz. 👍

Jetzt zur **Entscheidung**, klar und begründet:

---

## Empfehlung: **Track B3 (Result Integrity) zuerst abschließen**

**Kurz:**
👉 **Ja, wir sollten Track B mit B3 sauber zumachen, bevor wir zu Track A wechseln.**

### Warum diese Reihenfolge objektiv richtig ist

Du hast jetzt:

* **B1 Backpressure** → schützt vor Überlast & Retry-Stürmen
* **B2 Idempotency** → schützt vor Doppelverarbeitung & logischen Duplikaten

Was noch fehlt, um die **Data-Plane als abgeschlossen & vertrauenswürdig** zu markieren:

* ❌ **Integrität der Ergebnisse selbst**

Ohne B3 gilt:

> *„Wir wissen, dass ein Job nur einmal läuft – aber wir wissen nicht sicher, ob das Resultat unterwegs manipuliert wurde.“*

Das ist **genau die letzte Lücke der Data-Plane**.

---

## Abgrenzung: Warum **nicht** jetzt Track A?

Track A (Governance / Token Rotation / Attestation) ist **Control-Plane-Logik**.
Sie macht erst dann Sinn, wenn:

* die **Data-Plane semantisch vollständig** ist
* Results als **vertrauenswürdige Artefakte** gelten

Governance auf einer Data-Plane ohne Result-Integrity wäre:

* formal korrekt
* aber logisch unvollständig

---

## Was B3 wirklich abschließt (Scope-Klarheit)

Mit **B3 Result Integrity** erreichst du:

* **End-to-End-Vertrauen**:

  * submit → process → result → verify
* **Auditierbare Sicherheit**:

  * Manipulation = harter Fehler + Audit + Metric
* **Saubere Grenze**:

  * *Alles ab hier ist Policy, nicht Technik*

Danach kannst du Track B **final schließen** mit gutem Gewissen.

---

## Empfohlene B3-Strategie (kurz vorab)

Ich würde **zweistufig** vorgehen (ohne Overengineering):

### B3.1 (Pflicht, minimal)

* Canonical JSON
* `SHA256(result_payload)`
* Verify on result ingestion
* Audit Event: `RESULT_INTEGRITY_FAIL`

### B3.2 (optional, aber sehr stark)

* HMAC über canonical result
* Key:

  * entweder `SHERATAN_RESULT_HMAC_KEY`
  * oder bewusst **nicht** Hub-Token (Trennung von Auth vs Integrity)

Das bleibt **voll kompatibel** mit allem, was du jetzt hast.

---

## Klare Entscheidungsempfehlung

**➡️ Nächster Schritt: Track B3 – Result Integrity (v2.3)**
Danach:

* Track B = **DONE / CLOSED**
* Track A = **Governance Layer auf stabilem Fundament**

Wenn du willst, mache ich **jetzt direkt**:

> **Implementierungsplan v2.3 — Track B3 (Result Integrity)**
> im exakt gleichen Stil wie B1/B2 (Scope, ENV, Hooks, Tests, DoD).

Sag einfach: **„go b3“**.
✅ Go B3. Hier ist das **Execution-Paket v2.3.0 — Track B3: Result Integrity**, sauber kompatibel mit B1/B2 (Backpressure + Idempotency) und mit deinem Hardened Baseline Setup. 

---

# Track B3 Execution Package (v2.3.0) — Result Integrity

## 1) Ziel (B3 only)

Sicherstellen, dass **Results** auf der Data-Plane (8788) **nicht still manipulierbar** sind.

**Outcome:**

* Jeder Result-Payload trägt eine **Integrity Mark** (SHA256 oder HMAC).
* Hub **verifiziert** beim Ingest / Sync.
* Mismatch ⇒ **Reject + Audit + Metric**.

> Kein Eingriff in Port Split / Token / Leak-Guard / Control-Plane. Baseline bleibt unberührt. 

---

## 2) Integrity Levels (staged, aber B3 liefert direkt Value)

### Level 1 (Minimum, default)

* Canonical JSON serialization
* `result_sha256 = SHA256(canonical_json(result_payload))`

### Level 2 (Recommended, optional)

* `result_sig = HMAC_SHA256(SHERATAN_RESULT_HMAC_KEY, canonical_json(result_payload))`

**Wichtig:** Trenne Auth-Token von Integrity-Key:

* Auth: `SHERATAN_HUB_TOKEN`
* Integrity: `SHERATAN_RESULT_HMAC_KEY`

So kannst du Rotation/Policy später sauber machen (Track A).

---

## 3) API Contract (8788 Data)

### Result Ingestion Endpoint

Du hast typischerweise eines von:

* `POST /mesh/results/submit`
* oder `POST /mesh/sync_result`
* oder Core-Sync Path (falls Worker via Core geht)

**B3 Hook:** genau dort, wo Results “final” angenommen werden.

### Payload Erweiterung (minimal)

```json
{
  "job_id": "job_123",
  "ok": true,
  "result": { "...": "..." },

  "integrity": {
    "mode": "sha256|hmac",
    "sha256": "hex...",
    "sig": "hex..."  // only for hmac
  }
}
```

Backward compat:

* Wenn `SHERATAN_RESULT_INTEGRITY_REQUIRED=0`: accept ohne integrity (log warn)
* Wenn required=1: reject ohne integrity (400)

---

## 4) Canonicalization (kritisch)

### Canonical JSON rule

* sort keys
* no whitespace
* UTF-8
* stable floats (best effort)

Canonical payload sollte **nur** den semantischen Result-Body enthalten, nicht Transportfelder:

**Hash/Input** = canonical_json({

* `job_id`
* `ok`
* `result`
* optional: `error` (bei ok=false)
  })

Nicht inkludieren:

* timestamps
* node_id (optional, kann später in Attestation)
* headers

---

## 5) Verification Logic

### On ingest:

1. `mode = env default` wenn payload.integrity.mode fehlt
2. compute expected sha256
3. compare:

   * sha256 mismatch ⇒ **422 Unprocessable Entity** (oder 400) + `RESULT_INTEGRITY_FAIL`
4. if hmac mode:

   * compute expected sig and compare
   * mismatch ⇒ reject + audit + metric

### On mismatch:

* Response:

```json
{"ok": false, "error": "result_integrity_fail"}
```

* Audit event:

  * `RESULT_INTEGRITY_FAIL`
  * fields: job_id, mode, reason (`missing_integrity|sha_mismatch|sig_mismatch`), remote_addr, ts
  * **no payload dump**

* Metrics:

  * `integrity_fail_1m += 1`

---

## 6) ENV Defaults (v2.3)

* `SHERATAN_RESULT_INTEGRITY_MODE=sha256`  *(sha256 default)*
* `SHERATAN_RESULT_INTEGRITY_REQUIRED=1`   *(prod recommended)*
* Optional:

  * `SHERATAN_RESULT_HMAC_KEY=<secret>` (only if mode=hmac)
  * `SHERATAN_RESULT_CANONICAL_VERSION=1` (future-proof)

---

## 7) Files (minimal additions)

* `hub/result_integrity.py`

  * `canonicalize_result(payload)`
  * `compute_sha256(canonical)`
  * `compute_hmac(canonical, key)`
  * `verify(payload, env)`

* `hub/state.py`

  * reuse `write_atomic` (already centralized by you)

* `hub/data_plane.py` (or wherever results endpoint lives)

  * call `verify()` before accepting results

* `hub/metrics.py`

  * add:

    * `integrity_fail_1m`
    * `integrity_missing_1m`
    * `integrity_verified_1m`

* `hub/audit.py` (or existing audit logger)

  * new event types

---

## 8) Tests (Automated)

### `tests/test_result_integrity.py`

1. **Valid SHA256 accepted**
2. **Tampered result rejected**

   * change 1 field in `result`
   * keep old sha → expect reject + audit + metric
3. **Missing integrity rejected** (if required=1)
4. **HMAC mode**

   * valid sig accepted
   * wrong sig rejected

### Regression

* B1 (429/defers/reaper) still green
* B2 (dedup/collision/cache) still green
* smoke_checks still green baseline 

---

## 9) Manual Verification (Operator)

* submit job
* craft correct integrity → accept
* change `result.foo` but keep sha → reject
* check:

  * audit log contains `RESULT_INTEGRITY_FAIL`
  * `/metrics` shows `integrity_fail_1m` increment

---

## 10) DoD (B3 done when)

* [ ] Results without integrity are rejected (prod) or warned (dev switch)
* [ ] Tampered results are rejected
* [ ] Audit + metrics reflect failures without leaking content
* [ ] No regression to baseline isolation/token/leak-guard

---

## 11) Track B Closure Criteria

Nach B3 ist Track B **komplett**:

* B1 Backpressure ✅
* B2 Idempotency ✅
* B3 Result Integrity ✅

Dann ist der Wechsel zu **Track A (Governance / Token Rotation / Attestation)** logisch und sauber.

---

Wenn du willst, kann ich dir direkt im Anschluss **ein kleines PowerShell “B3 verify” Script** liefern (analog zu deinem B2 Script), das einen result payload canonicalisiert, SHA256 berechnet und dann einmal valid + einmal tampered an den Hub schickt.

Alles klar — hier ist ein **B3 Verify Script (PowerShell)**, das:

1. einen **validen** Result-Submit mit korrekt berechneter SHA256-Integrity schickt → **PASS erwartet**
2. danach den Result-Payload **tampered** (ändert ein Feld) aber behält die alte SHA256 → **REJECT erwartet**
3. optional einen **missing integrity** Test (wenn `SHERATAN_RESULT_INTEGRITY_REQUIRED=1`) → **REJECT erwartet**
4. am Ende `/metrics` abfragt (falls dein Metrics-Endpoint dort zählt)

> Du musst nur **den Result-Endpoint** eintragen, weil du evtl. `POST /mesh/results/submit` oder etwas anderes nutzt.
> Standard im Script: `http://localhost:8788/mesh/results/submit`

---

```powershell
# verify_b3_result_integrity.ps1
# Manual verification for Track B3 (Result Integrity)
# Requires: SHERATAN_HUB_TOKEN in env
# Assumes: SHERATAN_RESULT_INTEGRITY_MODE=sha256 (default)
# Endpoint: set $ResultEndpoint to your actual endpoint

$ErrorActionPreference = "Stop"

$BaseUrl = "http://localhost:8788"
$ResultEndpoint = "$BaseUrl/mesh/results/submit"   # <-- CHANGE if needed
$MetricsEndpoint = "$BaseUrl/metrics"
$Token = $env:SHERATAN_HUB_TOKEN

if ([string]::IsNullOrWhiteSpace($Token)) {
  throw "SHERATAN_HUB_TOKEN is not set in environment."
}

function Get-CanonicalJson([object]$obj) {
  # Deterministic, stable JSON: sort keys, no indentation.
  # PowerShell's ConvertTo-Json is not fully canonical across all types,
  # but for this test (simple objects) it's adequate if your server uses the same rule.
  # If your server uses a stricter canonicalizer, prefer computing sha server-side or align rules.
  return ($obj | ConvertTo-Json -Depth 20 -Compress)
}

function Get-Sha256Hex([string]$text) {
  $sha = [System.Security.Cryptography.SHA256]::Create()
  $bytes = [System.Text.Encoding]::UTF8.GetBytes($text)
  $hash = $sha.ComputeHash($bytes)
  ($hash | ForEach-Object { $_.ToString("x2") }) -join ""
}

function Invoke-JsonPost($url, $bodyObj) {
  $json = $bodyObj | ConvertTo-Json -Depth 20 -Compress
  try {
    return Invoke-RestMethod -Method Post -Uri $url -Body $json -ContentType "application/json" -Headers @{
      "X-Sheratan-Token" = $Token
    }
  } catch {
    $resp = $_.Exception.Response
    if ($resp -and $resp.StatusCode) {
      $status = [int]$resp.StatusCode
      $reader = New-Object System.IO.StreamReader($resp.GetResponseStream())
      $body = $reader.ReadToEnd()
      return [pscustomobject]@{ __http_status = $status; __http_body = $body }
    }
    throw
  }
}

function Try-Get($url) {
  try {
    return Invoke-RestMethod -Method Get -Uri $url -Headers @{ "X-Sheratan-Token" = $Token }
  } catch {
    return $null
  }
}

function Assert($cond, $msg) {
  if (-not $cond) { throw "ASSERT FAIL: $msg" }
  Write-Host "PASS: $msg" -ForegroundColor Green
}

Write-Host "== Track B3 Manual Verification (Result Integrity) ==" -ForegroundColor Cyan
Write-Host "ResultEndpoint: $ResultEndpoint" -ForegroundColor DarkCyan

# --------------------------
# Build a minimal "result payload" that should be integrity-protected
# (Must match your server's canonicalization inclusion rules.)
# --------------------------
$jobId = "test-b3-" + ([Guid]::NewGuid().ToString("N"))
$core = @{
  job_id = $jobId
  ok = $true
  result = @{
    value = 42
    note  = "hello"
  }
}

# Compute integrity over the semantic core (job_id, ok, result)
$canonical = Get-CanonicalJson $core
$sha = Get-Sha256Hex $canonical

$valid = @{
  job_id = $jobId
  ok = $true
  result = $core.result
  integrity = @{
    mode = "sha256"
    sha256 = $sha
  }
}

Write-Host "`n--- T1: Valid integrity should be accepted ---" -ForegroundColor Yellow
$r1 = Invoke-JsonPost $ResultEndpoint $valid

# Accept style differs per implementation: handle both {ok:true} and HTTP status objects
if ($r1.PSObject.Properties.Name -contains "__http_status") {
  throw "Expected accept, got HTTP $($r1.__http_status): $($r1.__http_body)"
} else {
  Assert ($r1.ok -eq $true) "valid result accepted (ok=true)"
}

# --------------------------
# Tamper result but keep old sha => must reject
# --------------------------
Write-Host "`n--- T2: Tampered payload with old sha must be rejected ---" -ForegroundColor Yellow
$tampered = @{
  job_id = $jobId
  ok = $true
  result = @{
    value = 43   # changed
    note  = "hello"
  }
  integrity = @{
    mode = "sha256"
    sha256 = $sha  # old sha (should now mismatch)
  }
}

$r2 = Invoke-JsonPost $ResultEndpoint $tampered
if ($r2.PSObject.Properties.Name -contains "__http_status") {
  # Expect 400/422
  Assert (($r2.__http_status -eq 400) -or ($r2.__http_status -eq 422)) "tampered result rejected (HTTP 400/422)"
  Write-Host "INFO: reject body: $($r2.__http_body)" -ForegroundColor DarkGray
} else {
  Assert ($r2.ok -eq $false) "tampered result rejected (ok=false style)"
}

# --------------------------
# Missing integrity (optional): if REQUIRED=1 it should reject
# --------------------------
Write-Host "`n--- T3: Missing integrity (optional) ---" -ForegroundColor Yellow
$missing = @{
  job_id = "test-b3-missing-" + ([Guid]::NewGuid().ToString("N"))
  ok = $true
  result = @{ value = 1 }
}

$r3 = Invoke-JsonPost $ResultEndpoint $missing
if ($r3.PSObject.Properties.Name -contains "__http_status") {
  if (($r3.__http_status -eq 400) -or ($r3.__http_status -eq 422) -or ($r3.__http_status -eq 403)) {
    Write-Host "PASS: missing integrity rejected (HTTP $($r3.__http_status))" -ForegroundColor Green
  } else {
    Write-Host "WARN: missing integrity not rejected (HTTP $($r3.__http_status)) - check SHERATAN_RESULT_INTEGRITY_REQUIRED" -ForegroundColor DarkYellow
  }
} else {
  if ($r3.ok -eq $false) {
    Write-Host "PASS: missing integrity rejected (ok=false style)" -ForegroundColor Green
  } else {
    Write-Host "WARN: missing integrity accepted - check SHERATAN_RESULT_INTEGRITY_REQUIRED" -ForegroundColor DarkYellow
  }
}

# --------------------------
# Metrics snapshot (best effort)
# --------------------------
Write-Host "`n--- T4: Metrics snapshot (best effort) ---" -ForegroundColor Yellow
$m = Try-Get $MetricsEndpoint
if ($null -ne $m) {
  Write-Host "INFO: metrics response:" -ForegroundColor DarkGray
  Write-Host ($m | ConvertTo-Json -Depth 10) -ForegroundColor DarkGray
  Write-Host "NOTE: Look for integrity_fail_1m increment after T2." -ForegroundColor DarkYellow
} else {
  Write-Host "SKIP: Could not fetch metrics (endpoint or auth differs)." -ForegroundColor DarkYellow
}

Write-Host "`nALL DONE: Track B3 manual verification finished." -ForegroundColor Cyan
```

---

## Nutzung

```powershell
$env:SHERATAN_HUB_TOKEN="…"
.\verify_b3_result_integrity.ps1
```

### Falls dein Result-Endpoint anders heißt

Im Script oben einfach ändern:

```powershell
$ResultEndpoint = "http://localhost:8788/<dein-endpoint>"
```

---

## Wichtiger Hinweis (Canonicalization)

PowerShells `ConvertTo-Json` ist für einfache Objekte stabil genug, aber wenn dein Hub eine strengere Canonicalization nutzt (z. B. spezielle Float-/Unicode-Regeln), kann es sein, dass der “valid” Test scheitert, obwohl B3 korrekt ist.

Wenn das passiert, sag mir kurz:

* **welche Canonicalization-Regel** du serverseitig nutzt (oder den relevanten snippet),
  dann passe ich das Script so an, dass es **bytegenau** identisch canonicalisiert wie dein Server.
