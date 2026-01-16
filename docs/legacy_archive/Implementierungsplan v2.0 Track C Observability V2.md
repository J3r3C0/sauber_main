Perfekt. Dann hier der **konkrete Implementierungsplan v2.x** – **Track C: Observability V2** – sauber versioniert, baseline-sicher und direkt umsetzbar.

> **Voraussetzung / Freeze:**
> Die v1.5 *Production-Hardened Baseline* bleibt unverändert und ist Referenzpunkt für alle DoD-Checks. 
> Ports, ENV und Runbook sind bindend.

---

# Implementierungsplan v2.0 — Track C: Observability V2

## Zielbild (warum dieser Track zuerst)

* **Messbarkeit vor Verhalten**: Bevor Data-Plane-Last & Governance kommen, hast du klare Signale.
* **Read-only & risikoarm**: Keine Änderung an Control/Data-Semantik.
* **Operativ nutzbar**: Alerts + Diagnose in Sekunden.

---

## C1. Metrics Endpoint (read-only)

### Scope

Ein minimaler Metrics-Endpoint pro Plane, **ohne Secrets**, **ohne Mutationen**.

### Endpoints

* **8787 (Control):** `GET /metrics`

  * `nodes_online`
  * `nodes_stale`
  * `nodes_dead`
  * `auth_fail_rate_1m`
  * `port_mismatch_rate_1m`
* **8788 (Data):** `GET /metrics`

  * `queue_depth`
  * `inflight_jobs`
  * `retry_rate_1m`

> Format: JSON (Prometheus-Style optional, aber nicht nötig in v2.0)

### Files

* `hub/metrics.py`
* `hub/serve_gateway.py` (router mount, read-only)

### DoD

* `/metrics` erreichbar auf beiden Ports
* Keine Token-Leaks, keine PII
* `.\smoke_checks.ps1` bleibt **grün**
* Metrics verändern keinen State

---

## C2. Audit Watcher (Alert Hooks)

### Scope

Ein leichter Watcher für
`C:\gemmaloop\.sheratan\logs\hub_security_audit.jsonl`

### Regeln (konfigurierbar)

* **AUTH_FAILURE** > *N*/min → ALERT
* **PORT_MISMATCH** > *N*/min → ALERT
* optional: Burst-Ignore für `127.0.0.1`

### Output

* `alerts.jsonl` (lokal)
* Konsolen-Summary (optional)

### Files

* `hub/audit_watcher.py`
* optional: `configs/alert_rules.json`

### DoD

* Simulierter Burst → Alert geschrieben
* Kein Token im Alert
* Watcher kann gestoppt/gestartet werden, ohne Hub zu beeinflussen

---

## C3. One-Command Diagnose-Bundle

### Scope

Ein reproduzierbares Diagnose-Artefakt für Ops & Debug.

### Script

* `scripts/diagnose.ps1`

### Inhalt des Bundles

* `/health` (8787 + 8788)
* Registry Snapshot (sanitized)
* letzte 200 Zeilen:

  * Hub-Control-Log
  * Hub-Data-Log
  * `hub_security_audit.jsonl`
* aktuelle ENV-Keys (nur Namen, keine Werte)

### Output

* `diag_bundle_<timestamp>.zip`

### DoD

* Läuft offline
* Enthält **keine Secrets**
* Bundle ist vollständig reproduzierbar

---

## Tests (neu, zusätzlich zu Smoke)

### Automated

* `tests/test_metrics.py`
* `tests/test_audit_watcher.py`

### Manual

```powershell
.\smoke_checks.ps1
Invoke-RestMethod http://localhost:8787/metrics
Invoke-RestMethod http://localhost:8788/metrics
.\scripts\diagnose.ps1
```

**Erwartung:** Alles grün, keine Regression zur Baseline.

---

## Dokumentation

### Update:

* `system_overview.md`

  * Abschnitt **“Observability V2”**
  * Metrics-Keys erklärt
  * Alert-Interpretation
  * Diagnose-Bundle-Workflow

> Runbook **erweitern**, nicht ersetzen. 

---

## Gatekeeper (Abbruchkriterien)

Der Track gilt **nur dann als DONE**, wenn:

* ✅ v1.5 Smoke Suite unverändert grün bleibt 
* ✅ Keine Änderung an Port-Isolation / Leak-Guard / Token-Logik
* ✅ Observability ist strikt read-only
* ✅ Diagnose-Bundle enthält keine Secrets

---

### Ergebnis nach Track C

Du hast:

* Echtzeit-Signale (Metrics)
* Frühe Warnungen (Alerts)
* Schnelle Forensik (Bundle)

👉 **Danach** ist das System bereit für **Track B (Data-Plane V2)**, ohne blind zu fliegen.

Wenn du willst, mache ich als nächsten Schritt **Track B – Implementierungsplan v2.1** im gleichen Detailgrad.
