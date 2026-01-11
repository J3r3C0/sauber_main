#!/usr/bin/env python3
import json, time, threading, math
from pathlib import Path

QFILE = Path("./_quorum.json")
QLOG  = Path("./_quorum_log.json")
QPOL  = Path("./_quorum_policy.json")
_LOCK = threading.Lock()

DEFAULT_POLICY = {
    "global": {
        "weight_default": 1.0,
        "weights": {},                 # node_id -> base weight
        "decay_half_life_s": 0,        # 0 = no decay
        "max_age_s": 0                 # 0 = infinite
    },
    "kind_overrides": {
        # "upload": {"decay_half_life_s": 0, "max_age_s": 0},
        # "job":    {"decay_half_life_s": 0, "max_age_s": 0},
        # "token":  {"decay_half_life_s": 0, "max_age_s": 0},
    }
}

def _read_json(p: Path, default):
    if p.exists():
        try: return json.loads(p.read_text(encoding="utf-8"))
        except Exception: return default
    return default

def _write_json(p: Path, obj):
    p.write_text(json.dumps(obj, indent=2), encoding="utf-8")

def _now(): return int(time.time())

def _find(recs, id_, kind):
    for r in recs:
        if r.get("id")==id_ and r.get("kind")==kind:
            return r
    return None

def _load_policy():
    pol = _read_json(QPOL, DEFAULT_POLICY.copy())
    pol.setdefault("global", {})
    pol["global"].setdefault("weight_default", 1.0)
    pol["global"].setdefault("weights", {})
    pol["global"].setdefault("decay_half_life_s", 0)
    pol["global"].setdefault("max_age_s", 0)
    pol.setdefault("kind_overrides", {})
    return pol

def _eff_weight(base, age_s, hl, max_age):
    if max_age and age_s > max_age:
        return 0.0
    if hl and age_s>0:
        return float(base) * (0.5 ** (age_s/hl))
    return float(base)

def _policy_for_kind(kind):
    pol = _load_policy()
    g = pol["global"]
    o = pol["kind_overrides"].get(kind, {})
    # resolved view
    return {
        "weight_default": float(g.get("weight_default", 1.0)),
        "weights": dict(g.get("weights", {})),
        "decay_half_life_s": int(o.get("decay_half_life_s", g.get("decay_half_life_s", 0))),
        "max_age_s": int(o.get("max_age_s", g.get("max_age_s", 0))),
    }

def _sum_weights(acks, pol_resolved):
    s = 0.0; now = _now()
    hl = pol_resolved.get("decay_half_life_s", 0)
    ma = pol_resolved.get("max_age_s", 0)
    for a in acks:
        ts = a.get("ts", now)
        age = max(0, now - ts)
        base = a.get("w", pol_resolved.get("weight_default", 1.0))
        s += _eff_weight(base, age, hl, ma)
    return s

def _normalize_acks(r, pol_resolved=None):
    if r.get("acks") and isinstance(r["acks"], list) and r["acks"] and isinstance(r["acks"][0], str):
        ids = list(dict.fromkeys(r["acks"]))  # unique, keep order
        default_w = pol_resolved.get("weight_default", 1.0) if pol_resolved else 1.0
        r["acks"] = [{"id": nid, "ts": _now(), "w": default_w} for nid in ids]

def set_policy(weight_default=None, decay_half_life_s=None, max_age_s=None, weights_patch=None):
    with _LOCK:
        pol = _load_policy()
        if weight_default is not None: pol["global"]["weight_default"] = float(weight_default)
        if decay_half_life_s is not None: pol["global"]["decay_half_life_s"] = int(decay_half_life_s)
        if max_age_s is not None: pol["global"]["max_age_s"] = int(max_age_s)
        if isinstance(weights_patch, dict):
            for k,v in weights_patch.items():
                pol["global"]["weights"][k] = float(v)
        _write_json(QPOL, pol)
        return pol

def set_kind_policy(kind: str, decay_half_life_s=None, max_age_s=None):
    with _LOCK:
        pol = _load_policy()
        po = pol["kind_overrides"].get(kind, {})
        if decay_half_life_s is not None: po["decay_half_life_s"] = int(decay_half_life_s)
        if max_age_s is not None: po["max_age_s"] = int(max_age_s)
        pol["kind_overrides"][kind] = po
        _write_json(QPOL, pol)
        return pol

def get_policy(kind: str=None):
    return _policy_for_kind(kind) if kind else _load_policy()

def create_or_get(id_: str, kind: str, required: float, meta: dict=None):
    with _LOCK:
        recs = _read_json(QFILE, [])
        r = _find(recs, id_, kind)
        if r is None:
            r = {"id": id_, "kind": kind, "required": float(required),
                 "acks": [], "finalized": False, "meta": meta or {}, "ts": _now()}
            recs.append(r); _write_json(QFILE, recs)
        else:
            _normalize_acks(r, _policy_for_kind(kind))
        return r

def add_ack(id_: str, kind: str, node_id: str):
    with _LOCK:
        recs = _read_json(QFILE, [])
        r = _find(recs, id_, kind)
        if r is None:
            r = {"id": id_, "kind": kind, "required": 1.0, "acks": [], "finalized": False, "meta": {}, "ts": _now()}
            recs.append(r)
        polr = _policy_for_kind(kind)
        _normalize_acks(r, polr)
        base_w = float(polr.get("weights", {}).get(node_id, polr.get("weight_default", 1.0)))
        found = False
        for a in r["acks"]:
            if a.get("id")==node_id:
                a["ts"] = _now(); a["w"] = base_w; found = True; break
        if not found:
            r["acks"].append({"id": node_id, "ts": _now(), "w": base_w})
        if not r["finalized"]:
            total = _sum_weights(r["acks"], polr)
            if total >= float(r["required"]):
                r["finalized"] = True
                log = _read_json(QLOG, [])
                log.append({"id": r["id"], "kind": r["kind"], "sum_w": total,
                            "required": r["required"], "meta": r.get("meta",{}),
                            "finalized_ts": _now()})
                _write_json(QLOG, log)
        _write_json(QFILE, recs)
        total_now = _sum_weights(r["acks"], polr)
        return {"ok": True, "finalized": r["finalized"], "sum_w": round(total_now, 6), "required": float(r["required"])}

def is_finalized(id_: str, kind: str) -> bool:
    r = _find(_read_json(QFILE, []), id_, kind); return bool(r and r.get("finalized"))

def get_record(id_: str, kind: str):
    r = _find(_read_json(QFILE, []), id_, kind)
    if r: _normalize_acks(r, _policy_for_kind(kind))
    return r

def list_records(kind: str=None):
    recs = _read_json(QFILE, [])
    out = []
    for r in recs:
        if kind is None or r.get("kind")==kind:
            polr = _policy_for_kind(r.get("kind"))
            _normalize_acks(r, polr)
            rr = dict(r)
            rr["_sum_w"] = _sum_weights(r["acks"], polr)
            out.append(rr)
    return out
