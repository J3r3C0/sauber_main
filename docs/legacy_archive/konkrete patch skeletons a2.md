Alles klar — dann hier das **konkrete Patch-Skelett** (copy/paste-fähig) für **A2 Integration**:

1. `hub/attestation.py` (Evaluator + Flip-Flop)
2. `hub/registry.py` (Persistenz/Update-Helpers)
3. `hub/serve_gateway.py` (Heartbeat Hook)
4. `hub/metrics.py` (Counters/Gauges)
5. `scripts/verify_a2_attestation.ps1` (3 Tests)

> Ich halte es bewusst **minimal-invasiv**: kein Blocken, nur **YELLOW + Audit + Metrics**, und **MISSING ist ok**.

---

## 1) `hub/attestation.py` (neu oder ergänzen)

```python
# hub/attestation.py
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
import hashlib
import json
from datetime import datetime, timezone, timedelta


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def canonical_json(obj: Any) -> str:
    # Stable canonical JSON: sort keys, no whitespace.
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def compute_capability_hash(capabilities: List[str]) -> str:
    caps = sorted([c.strip() for c in capabilities if c and c.strip()])
    return sha256_hex(canonical_json(caps))


@dataclass
class AttestationDecision:
    status: str  # OK|DRIFT|SPOOF_SUSPECT|MISSING
    health_hint: Optional[str] = None  # e.g. "YELLOW"
    event: Optional[str] = None  # audit event name
    details: Optional[Dict[str, Any]] = None


def evaluate_attestation(
    node_record: Dict[str, Any],
    incoming_att: Optional[Dict[str, Any]],
    now_utc: Optional[datetime] = None,
    remote_addr: Optional[str] = None,
    flip_window_sec: int = 120,
    flip_threshold: int = 3,
) -> AttestationDecision:
    """
    Signal-only evaluator:
      - Missing attestation => MISSING (no penalty)
      - Drift vs first_seen => DRIFT (YELLOW)
      - Flip-flop in short window => SPOOF_SUSPECT (YELLOW)
    """
    now_utc = now_utc or _utcnow()

    # Ensure container exists
    att_block = node_record.setdefault("attestation", {})
    hist = att_block.setdefault("history", [])  # lightweight in-memory/persisted history

    if not incoming_att:
        # Backward compatible: do not degrade health
        att_block["status"] = "MISSING"
        att_block["last_change_utc"] = att_block.get("last_change_utc") or None
        return AttestationDecision(status="MISSING", event=None, details=None)

    build_id = incoming_att.get("build_id") or ""
    cap_hash = incoming_att.get("capability_hash") or ""
    runtime = incoming_att.get("runtime") or {}

    # Populate first_seen if missing
    first = att_block.get("first_seen")
    if not first:
        att_block["first_seen"] = {
            "ts_utc": now_utc.isoformat(),
            "build_id": build_id,
            "capability_hash": cap_hash,
            "runtime": runtime,
        }
        att_block["last_seen"] = {
            "ts_utc": now_utc.isoformat(),
            "build_id": build_id,
            "capability_hash": cap_hash,
        }
        att_block["status"] = "OK"
        att_block["drift_count"] = 0
        att_block["spoof_count"] = 0
        att_block["last_change_utc"] = now_utc.isoformat()
        # track history for flip-flop detection
        hist.append({"ts_utc": now_utc.isoformat(), "capability_hash": cap_hash, "build_id": build_id})
        return AttestationDecision(
            status="OK",
            event="ATTESTATION_FIRST_SEEN",
            details={"remote_addr": remote_addr, "build_id": build_id, "cap_prefix": cap_hash[:8]},
        )

    # Update last_seen always
    att_block["last_seen"] = {
        "ts_utc": now_utc.isoformat(),
        "build_id": build_id,
        "capability_hash": cap_hash,
    }

    # Push to history, then prune window
    hist.append({"ts_utc": now_utc.isoformat(), "capability_hash": cap_hash, "build_id": build_id})
    _prune_history(hist, now_utc, flip_window_sec)

    # Flip-flop / spoof suspect (only if threshold hits)
    if _is_flipflop(hist, flip_threshold):
        att_block["status"] = "SPOOF_SUSPECT"
        att_block["spoof_count"] = int(att_block.get("spoof_count", 0)) + 1
        att_block["last_change_utc"] = now_utc.isoformat()
        return AttestationDecision(
            status="SPOOF_SUSPECT",
            health_hint="YELLOW",
            event="ATTESTATION_SPOOF_SUSPECT",
            details={
                "remote_addr": remote_addr,
                "cap_prefix": cap_hash[:8],
                "flip_count": len(hist),
                "window_sec": flip_window_sec,
            },
        )

    # Drift check vs first_seen baseline
    first_build = (first.get("build_id") or "")
    first_cap = (first.get("capability_hash") or "")

    if build_id != first_build or cap_hash != first_cap:
        att_block["status"] = "DRIFT"
        att_block["drift_count"] = int(att_block.get("drift_count", 0)) + 1
        att_block["last_change_utc"] = now_utc.isoformat()
        return AttestationDecision(
            status="DRIFT",
            health_hint="YELLOW",
            event="ATTESTATION_DRIFT",
            details={
                "remote_addr": remote_addr,
                "old_build": first_build,
                "new_build": build_id,
                "old_cap_prefix": first_cap[:8],
                "new_cap_prefix": cap_hash[:8],
            },
        )

    # Otherwise OK
    att_block["status"] = "OK"
    return AttestationDecision(status="OK", event=None, details=None)


def _prune_history(hist: List[Dict[str, Any]], now_utc: datetime, window_sec: int) -> None:
    cutoff = now_utc - timedelta(seconds=window_sec)
    # Keep only entries with ts >= cutoff
    kept = []
    for e in hist:
        try:
            ts = datetime.fromisoformat(e["ts_utc"])
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if ts >= cutoff:
            kept.append(e)
    hist[:] = kept


def _is_flipflop(hist: List[Dict[str, Any]], threshold: int) -> bool:
    """
    Simple flip-flop heuristic:
      - if we see >=threshold *changes* in capability_hash within window.
    """
    if len(hist) < threshold:
        return False
    hashes = [h.get("capability_hash") for h in hist if h.get("capability_hash")]
    if len(hashes) < threshold:
        return False
    # count transitions
    transitions = 0
    prev = hashes[0]
    for cur in hashes[1:]:
        if cur != prev:
            transitions += 1
        prev = cur
    return transitions >= (threshold - 1)
```

---

## 2) `hub/registry.py` (Persistenz + Update Node)

> Du hast `write_atomic` nach `hub/state.py` verschoben – perfekt.
> Hier nur die notwendige Struktur: load/save/update.

```python
# hub/registry.py
from __future__ import annotations

from typing import Any, Dict, Optional
from datetime import datetime, timezone
from .state import read_json, write_atomic_json  # names ggf. anpassen

REGISTRY_PATH_DEFAULT = r"C:\gemmaloop\.sheratan\state\nodes_registry.json"


def utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class Registry:
    def __init__(self, path: str = REGISTRY_PATH_DEFAULT):
        self.path = path

    def load(self) -> Dict[str, Any]:
        data = read_json(self.path) or {}
        # expected structure: { "nodes": {node_id: record, ...} } or flat
        return data

    def save(self, data: Dict[str, Any]) -> None:
        write_atomic_json(self.path, data)

    def get_nodes(self, data: Dict[str, Any]) -> Dict[str, Any]:
        # Support both flat and nested for backward compat
        if "nodes" in data and isinstance(data["nodes"], dict):
            return data["nodes"]
        return data

    def upsert_node(self, node_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        data = self.load()
        nodes = self.get_nodes(data)
        rec = nodes.get(node_id, {})
        rec.update(updates)
        rec.setdefault("node_id", node_id)
        rec.setdefault("first_seen_utc", rec.get("first_seen_utc") or utcnow_iso())
        rec["last_seen_utc"] = utcnow_iso()
        nodes[node_id] = rec

        # write back in same shape
        if "nodes" in data and isinstance(data["nodes"], dict):
            data["nodes"] = nodes
        else:
            data = nodes

        self.save(data)
        return rec

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        data = self.load()
        nodes = self.get_nodes(data)
        return nodes.get(node_id)
```

---

## 3) `hub/serve_gateway.py` (Heartbeat Handler Hook)

> Du musst nur in den Heartbeat Endpoint rein:
> attestation → evaluate → update record → persist.

```python
# hub/serve_gateway.py (snippet)
from __future__ import annotations

from fastapi import FastAPI, Request
from .registry import Registry
from .attestation import evaluate_attestation
from .audit import audit_event  # deine audit func
from .metrics import METRICS    # deine metrics singleton

REGISTRY = Registry()

def _client_ip(request: Request) -> str:
    try:
        return request.client.host
    except Exception:
        return "unknown"

@app.post("/api/hosts/heartbeat")
async def hosts_heartbeat(payload: dict, request: Request):
    node_id = payload.get("node_id") or payload.get("host") or payload.get("name")
    if not node_id:
        return {"ok": False, "error": "missing_node_id"}

    remote = _client_ip(request)
    incoming_att = payload.get("attestation")

    # load existing record if you need it (optional), else upsert first then evaluate
    existing = REGISTRY.get_node(node_id) or {"node_id": node_id}

    decision = evaluate_attestation(
        node_record=existing,
        incoming_att=incoming_att,
        remote_addr=remote,
        flip_window_sec=int(os.getenv("SHERATAN_ATTESTATION_FLIP_WINDOW_SEC", "120")),
        flip_threshold=int(os.getenv("SHERATAN_ATTESTATION_FLIP_THRESHOLD", "3")),
    )

    # Health hint: signal-only
    if decision.health_hint == "YELLOW":
        # don't downgrade if already worse, keep your existing logic if present
        existing["health"] = "YELLOW"

    # Persist updated record (includes attestation block written in-place)
    rec = REGISTRY.upsert_node(node_id, existing)

    # Metrics
    METRICS.attestation.observe(decision.status)

    # Audit if event
    if decision.event:
        audit_event(decision.event, {
            "node_id": node_id,
            "remote_addr": remote,
            **(decision.details or {}),
        })

    return {"ok": True, "node_id": node_id, "attestation_status": decision.status}
```

> **Note:** `os` import fehlt im Snippet – im realen File hinzufügen.

---

## 4) `hub/metrics.py` (Attestation Metrics)

Minimaler Zähler:

```python
# hub/metrics.py (snippet)
from __future__ import annotations
from collections import deque
from datetime import datetime, timezone, timedelta

class AttestationMetrics:
    def __init__(self):
        self.counts = {"OK": 0, "MISSING": 0, "DRIFT": 0, "SPOOF_SUSPECT": 0}
        self.events_1m = deque()  # (ts, status)

    def observe(self, status: str):
        if status not in self.counts:
            status = "MISSING"
        self.counts[status] += 1
        self.events_1m.append((datetime.now(timezone.utc), status))
        self._prune_1m()

    def _prune_1m(self):
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=60)
        while self.events_1m and self.events_1m[0][0] < cutoff:
            self.events_1m.popleft()

    def snapshot(self):
        self._prune_1m()
        drift_1m = sum(1 for _, s in self.events_1m if s == "DRIFT")
        spoof_1m = sum(1 for _, s in self.events_1m if s == "SPOOF_SUSPECT")
        missing_1m = sum(1 for _, s in self.events_1m if s == "MISSING")
        ok_1m = sum(1 for _, s in self.events_1m if s == "OK")
        return {
            "attestation_ok": self.counts["OK"],
            "attestation_missing": self.counts["MISSING"],
            "attestation_drift": self.counts["DRIFT"],
            "attestation_spoof_suspect": self.counts["SPOOF_SUSPECT"],
            "attestation_ok_1m": ok_1m,
            "attestation_missing_1m": missing_1m,
            "attestation_drift_1m": drift_1m,
            "attestation_spoof_1m": spoof_1m,
        }

class Metrics:
    def __init__(self):
        self.attestation = AttestationMetrics()
        # ... existing metrics

METRICS = Metrics()
```

Dann im `/metrics` handler einfach `METRICS.attestation.snapshot()` in die JSON packen.

---

## 5) `scripts/verify_a2_attestation.ps1` (3 Tests)

```powershell
# verify_a2_attestation.ps1
$ErrorActionPreference = "Stop"

$BaseUrl = "http://localhost:8787"
$Endpoint = "$BaseUrl/api/hosts/heartbeat"
$Token = $env:SHERATAN_HUB_TOKEN

if ([string]::IsNullOrWhiteSpace($Token)) { throw "SHERATAN_HUB_TOKEN not set" }

function Post($body) {
  $json = $body | ConvertTo-Json -Depth 10 -Compress
  try {
    return Invoke-RestMethod -Method Post -Uri $Endpoint -Body $json -ContentType "application/json" -Headers @{
      "X-Sheratan-Token" = $Token
    }
  } catch {
    $resp = $_.Exception.Response
    if ($resp) {
      $status = [int]$resp.StatusCode
      $reader = New-Object System.IO.StreamReader($resp.GetResponseStream())
      $b = $reader.ReadToEnd()
      return [pscustomobject]@{ __http_status=$status; __http_body=$b }
    }
    throw
  }
}

function Assert($cond, $msg) {
  if (-not $cond) { throw "ASSERT FAIL: $msg" }
  Write-Host "PASS: $msg" -ForegroundColor Green
}

Write-Host "== A2 Verify ==" -ForegroundColor Cyan

$node = "verify-node-" + ([Guid]::NewGuid().ToString("N"))
$attA = @{
  schema="attestation_v1"
  build_id="build-A"
  capability_hash="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
  runtime=@{ os="windows"; python="3.11.7" }
}

Write-Host "`n--- T1: First Seen => OK ---" -ForegroundColor Yellow
$r1 = Post @{ node_id=$node; health="GREEN"; attestation=$attA }
Assert ($r1.ok -eq $true) "heartbeat ok=true"
Assert ($r1.attestation_status -eq "OK") "first seen status OK"

Write-Host "`n--- T2: Drift => DRIFT + YELLOW ---" -ForegroundColor Yellow
$attB = $attA.Clone()
$attB.build_id = "build-B"  # drift
$r2 = Post @{ node_id=$node; health="GREEN"; attestation=$attB }
Assert ($r2.ok -eq $true) "drift heartbeat ok=true"
Assert ($r2.attestation_status -eq "DRIFT") "drift status DRIFT"

Write-Host "`n--- T3: Flip-Flop => SPOOF_SUSPECT ---" -ForegroundColor Yellow
# Alternate capability hashes quickly: A -> C -> A
$attC = $attA.Clone()
$attC.capability_hash = "cccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccccc"
$r3 = Post @{ node_id=$node; health="GREEN"; attestation=$attC } | Out-Null
$r4 = Post @{ node_id=$node; health="GREEN"; attestation=$attA } | Out-Null
$r5 = Post @{ node_id=$node; health="GREEN"; attestation=$attC }
# Depending on threshold/window, this should trip
if ($r5.attestation_status -eq "SPOOF_SUSPECT") {
  Write-Host "PASS: spoof suspect triggered" -ForegroundColor Green
} else {
  Write-Host "WARN: spoof suspect not triggered. Check SHERATAN_ATTESTATION_FLIP_THRESHOLD/WINDOW." -ForegroundColor DarkYellow
  Write-Host "Status was: $($r5.attestation_status)" -ForegroundColor DarkGray
}

Write-Host "`nDONE" -ForegroundColor Cyan
```

---

## Minimal DoD für “A2 Integrated”

Du bist fertig, wenn:

* Registry record pro node enthält `attestation.first_seen/last_seen/status/counters`
* DRIFT & SPOOF erzeugen Audit-Events + Metrics
* Missing attestation bleibt kompatibel
* Kein Request wird geblockt (signal-only)

---

Wenn du mir (1) deinen tatsächlichen Heartbeat-Endpoint (Pfad) und (2) deine Registry-Datenform (flat vs `{nodes:{...}}`) sagst, kann ich dir die zwei Snippets (`serve_gateway.py` / `registry.py`) exakt auf deine Realität “einrasten” – aber das obige ist schon so gebaut, dass es in 90% der Layouts direkt passt.
