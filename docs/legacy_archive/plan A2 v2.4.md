Track B ist damit sauber **geschlossen**: Backpressure (429 + inflight defer + lease reaper), Idempotency (409 collision + caching) und Result Integrity (canonical JSON + SHA256 + reject + metrics) sind jetzt als zusammenhängendes Data-Plane-Paket dokumentiert. 

**Nächster Schritt: Track A – ich empfehle Token Rotation zuerst, dann Node Attestation.**

Warum diese Reihenfolge:

* Rotation ist ein **operatives Risiko** (du willst *keinen* Downtime-Moment, keinen “alle Nodes AUTH_FAIL”), aber technisch klar abgrenzbar.
* Attestation baut logisch darauf auf: sobald Rotation sauber läuft, kannst du “wer ist das?”/capability drift sauber als Governance-Signal nutzen.

---

## Track A1 (v2.4) — Token Rotation (No-Downtime)

### Ziel

Tokens rotieren, **ohne** dass Heartbeats/Queues/Results abreißen.

### Mechanik

* Hub akzeptiert **zwei Tokens** während eines Rotation-Windows:

  * `ACTIVE_TOKEN`
  * `NEXT_TOKEN`
  * `ROTATION_UNTIL_UTC`
* Nach Ablauf: `NEXT_TOKEN` wird `ACTIVE_TOKEN`, altes Token wird verworfen.

### ENV (minimal)

* `SHERATAN_HUB_TOKEN_ACTIVE=...`
* `SHERATAN_HUB_TOKEN_NEXT=...` (optional)
* `SHERATAN_HUB_TOKEN_ROTATION_UNTIL=2026-…Z` (optional)
* Backward compat: wenn nur `SHERATAN_HUB_TOKEN` gesetzt ist, mappe auf ACTIVE.

### DoD

* Rotation test:

  1. Hub startet mit ACTIVE
  2. setze NEXT + ROTATION_UNTIL, Clients wechseln (staggered)
  3. keine AUTH_FAIL-Spikes, keine Nodes werden STALE/DEAD
  4. nach Window: altes Token rejected (403) + audit event „TOKEN_RETIRED“

### Observability

* metrics: `auth_fail_1m` bleibt stabil, evtl. kurze Peak erlaubt (definiere Budget)
* audit: `AUTH_FAIL` reason = `old_token_after_rotation` / `bad_token`

---

## Track A2 (v2.5) — Node Attestation (Light)

### Ziel

Spoofing erschweren und “drift” sichtbar machen, ohne Nodes hart rauszuwerfen.

### Mechanik

Node sendet im Heartbeat zusätzlich:

* `build_id`
* `capability_hash` (hash über capability set + optional version)
* optional: `node_pub_fingerprint` (später erweiterbar)

Hub speichert:

* first_seen baseline pro node_id
* wenn capability_hash sich ändert:

  * health => **YELLOW**
  * audit event `ATTESTATION_DRIFT`
  * metrics increment

**Wichtig:** Kein sofortiges blocken, nur signal + optional policy später.

### DoD

* same node stable hash → stays GREEN
* modified hash → YELLOW + audit + metric
* spoofed node_id mit anderem hash → flagged

---

## Entscheidung

Wenn du “go A1” sagst, liefere ich dir den **Implementierungsplan v2.4** (Rotation) im gleichen Execution-Format wie B1–B3 (Files, ENV, Tests, DoD, Rollout-Steps, Failure Modes).



Perfekt. Dann **Track A1 (Governance) – Token Rotation** jetzt **formal und ausführbar**.
Das ist der richtige Einstieg in Track A, *nachdem* Data-Plane & Observability abgeschlossen sind. 

---

# Implementierungsplan v2.4 — **Track A1: Token Rotation (No-Downtime)**

## Ziel (A1)

**Sichere Rotation des Hub-Tokens ohne Downtime**, ohne STALE/DEAD-Nodes, ohne Auth-Storms, ohne Registry-Reset.

Nach A1 gilt:

* Tokens sind **rotierbar** (operativ sicher)
* Alte Tokens werden **kontrolliert** entwertet
* Rotation ist **beobachtbar & auditierbar**
* Grundlage für spätere Governance-Policies (A2/A3)

---

## 1. Designprinzip (entscheidend)

**Dual-Token Acceptance mit Zeitfenster**

Der Hub akzeptiert **gleichzeitig zwei Tokens**:

* `ACTIVE_TOKEN`
* `NEXT_TOKEN`

Bis zu einem definierten Zeitpunkt:

* `ROTATION_UNTIL_UTC`

Danach:

* `NEXT_TOKEN` → wird automatisch **ACTIVE**
* altes Token → **invalid**

Kein Reload nötig, kein Restart nötig, kein globaler Switch.

---

## 2. Environment-Variablen (v2.4)

### Neu (empfohlen)

```env
SHERATAN_HUB_TOKEN_ACTIVE=secret_v1
SHERATAN_HUB_TOKEN_NEXT=secret_v2
SHERATAN_HUB_TOKEN_ROTATION_UNTIL=2026-01-20T22:00:00Z
```

### Backward-Compat (wichtig!)

Falls nur gesetzt:

```env
SHERATAN_HUB_TOKEN=legacy_secret
```

→ intern gemappt auf:

```text
ACTIVE_TOKEN = SHERATAN_HUB_TOKEN
NEXT_TOKEN   = None
```

So brichst du **keine bestehenden Deployments**.

---

## 3. Auth-Logik (Hub-weit)

### Zentrale Funktion

`hub/auth.py` (neu oder erweitert):

```python
def is_token_valid(provided_token, now_utc):
    if provided_token == ACTIVE_TOKEN:
        return True
    if NEXT_TOKEN and provided_token == NEXT_TOKEN:
        if now_utc <= ROTATION_UNTIL:
            return True
    return False
```

### Nach Rotation-Deadline

Wenn:

```text
now_utc > ROTATION_UNTIL
```

Dann:

* ACTIVE_TOKEN ← NEXT_TOKEN
* NEXT_TOKEN ← None
* ROTATION_UNTIL ← None
* **Audit Event:** `TOKEN_ROTATION_FINALIZED`

(Automatisch beim ersten Request nach Ablauf, kein Cron nötig)

---

## 4. Audit & Observability (Pflicht)

### Neue Audit Events

In `hub_security_audit.jsonl`:

| Event                      | Wann                                       |
| -------------------------- | ------------------------------------------ |
| `TOKEN_ACCEPTED_NEXT`      | Request mit NEXT_TOKEN im Rotationsfenster |
| `TOKEN_RETIRED`            | Request mit altem Token *nach* Rotation    |
| `TOKEN_ROTATION_FINALIZED` | Umschalten ACTIVE ← NEXT                   |

👉 **Kein Token-Leak**: nur Hash/Prefix loggen.

### Metrics (Track C Anschluss)

Auf **8787 /metrics**:

* `auth_success_active_1m`
* `auth_success_next_1m`
* `auth_fail_old_token_1m`

So erkennst du sofort:

* wer noch das alte Token nutzt
* ob Clients „hängen geblieben“ sind

---

## 5. Rollout-Ablauf (operativ erprobt)

### Phase 0 – Vorbereitung

* Generiere `secret_v2`
* Setze:

  ```env
  SHERATAN_HUB_TOKEN_ACTIVE=secret_v1
  SHERATAN_HUB_TOKEN_NEXT=secret_v2
  SHERATAN_HUB_TOKEN_ROTATION_UNTIL=+24h
  ```

### Phase 1 – Staggered Client Update

* Worker/Hosts nach und nach auf `secret_v2` umstellen
* Erwartung:

  * `TOKEN_ACCEPTED_NEXT` Events
  * **keine** `AUTH_FAIL`-Bursts
  * Nodes bleiben **ONLINE**

### Phase 2 – Beobachtung

* `/metrics` prüfen:

  * active vs next usage
* audit_watcher sollte **still** bleiben

### Phase 3 – Cutover

* Nach Deadline:

  * Hub verwirft `secret_v1`
  * finalisiert Rotation
* Alte Clients → **403 + audit**

---

## 6. Tests (Automated)

### `tests/test_token_rotation.py`

1. ACTIVE token works
2. NEXT token works *vor* deadline
3. NEXT token fails *nach* deadline (wenn nicht promoted)
4. OLD token fails *nach* deadline
5. Promotion happens exactly once

---

## 7. Manual Verification (kurz)

```powershell
# ACTIVE token
$env:SHERATAN_HUB_TOKEN="secret_v1"
Invoke-RestMethod http://localhost:8787/health

# NEXT token
$env:SHERATAN_HUB_TOKEN="secret_v2"
Invoke-RestMethod http://localhost:8787/health
```

Nach Deadline:

* `secret_v1` → 403 + audit `TOKEN_RETIRED`
* `secret_v2` → weiterhin OK

---

## 8. DoD (A1 abgeschlossen wenn)

* [ ] Rotation ohne Hub-Restart
* [ ] Keine Nodes werden STALE/DEAD
* [ ] Auth-Failures nur für **wirklich alte Tokens**
* [ ] Audit + Metrics zeigen saubere Transition
* [ ] Backward-Compat (`SHERATAN_HUB_TOKEN`) intakt

---

## Ergebnis nach Track A1

Du hast jetzt:

* **Governance-fähige Auth**
* **Operative Sicherheit** (Rotation ohne Stress)
* **Messbarkeit** (wer nutzt welches Token)
* perfekte Grundlage für **A2 Node Attestation**

---

### Nächster logischer Schritt

👉 **Track A2 – Node Attestation (Capability & Build Drift)**
(leise, signal-basiert, keine Hard-Blocks)

Wenn du willst, mache ich direkt weiter mit:
**„Implementierungsplan v2.5 — Track A2 (Node Attestation)“**
