#!/usr/bin/env python3
import json, time, random, argparse, threading
from urllib.request import Request, urlopen
from urllib.error import URLError
from pathlib import Path

REPUTATION_FILE = Path("./_reputation.json")

def _load_rep():
    if REPUTATION_FILE.exists():
        return json.loads(REPUTATION_FILE.read_text(encoding="utf-8"))
    return {}

def _save_rep(rep):
    REPUTATION_FILE.write_text(json.dumps(rep, indent=2), encoding="utf-8")

def post(url, payload, timeout_s=5.0):
    data = json.dumps(payload).encode()
    req = Request(url, data=data, headers={"Content-Type":"application/json"})
    return json.loads(urlopen(req, timeout=timeout_s).read().decode())

def get(url, timeout_s=5.0):
    return json.loads(urlopen(url, timeout=timeout_s).read().decode())

def micro_auction(hosts, job, rep):
    # load mesh metrics if available
    from pathlib import Path as _P
    import json as _J
    mesh_m = None
    mf = _P('./mesh/last_metrics.json')
    if mf.exists():
        try:
            mesh_m = _J.loads(mf.read_text(encoding='utf-8'))
        except Exception:
            mesh_m = None
    # discovery map for via factors
    via_map = {}
    try:
        dmap = _J.loads(_P('./discovery/mesh_hosts.json').read_text(encoding='utf-8'))
        for ep, rec in dmap.items(): via_map[ep] = rec.get('via','udp')
    except Exception:
        pass
    neigh_count = 0
    path_metric = 256
    if mesh_m:
        neigh_count = len(mesh_m.get("neighbors", []))
        routes = mesh_m.get("routes", [])
        if routes:
            path_metric = min([r.get("metric", 256) for r in routes])
    scored = []
    for h in hosts:
        try:
            q = get(f"{h}/quote?type={job['type']}&size={job['size']}", timeout_s=job.get("quote_timeout_s", 2.0))
            lat = job.get("latency_ms", 1000)
            rep_penalty = 1.0 + 0.05 * rep.get(h, {}).get("misses", 0)  # simple penalty
            mesh_penalty = 1.0
            if mesh_m and not mesh_m.get('health',{}).get('mesh_ok', True):
                mesh_penalty = 1.2
            # neighbor bonus: more neighbors -> slight discount (up to ~10%)
            neighbor_factor = max(0.9, 1.0 - 0.02 * neigh_count)
            # path_metric factor: higher metric -> small penalty
            path_factor = 1.0 + (max(0, path_metric - 256)/1024.0)
            base = q["quote"] + (lat/1000.0)*0.01
            # via factor
            via = via_map.get(q['host'], 'udp')
            via_w = {'udp':1.0,'ble':1.05,'lora':1.1,'file':1.2}.get(via,1.1)
            score = base * rep_penalty * mesh_penalty * neighbor_factor * path_factor * via_w
            scored.append((score, h, q["quote"]))
        except Exception:
            continue
    scored.sort(key=lambda x: x[0])
    r = max(1, job.get("redundancy", 2))
    return scored[: r ]

def dispatch(host_url, job, t_activate_s):
    # Only support versioned JobSpec v1 now
    if "job" not in job:
        return False, {"error": "LEGACY_PAYLOAD_REJECTED", "msg": "Broker only accepts JobSpec v1"}
        
    payload = {
        "job_id": job.get("job_id"),
        "job": job["job"]
    }
    
    try:
        # enforce activation timeout at HTTP layer
        res = post(f"{host_url}/run", payload, timeout_s=t_activate_s)
        return True, res
    except URLError as e:
        return False, {"error": str(e)}
    try:
        # enforce activation timeout at HTTP layer
        res = post(f"{host_url}/run", payload, timeout_s=t_activate_s)
        return True, res
    except URLError as e:
        return False, {"error": str(e)}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--hosts", nargs="+", default=None)
    ap.add_argument("--jobs", type=int, default=3)
    ap.add_argument("--t_activate_s", type=float, default=30.0, help="Activation SLA, seconds")
    args = ap.parse_args()
    if args.hosts is None:
        # try discovery
        from pathlib import Path
        import json
        f = Path('./discovery/mesh_hosts.json')
        if f.exists():
            hosts_map = json.loads(f.read_text(encoding='utf-8'))
            args.hosts = list(hosts_map.keys())
        else:
            args.hosts = ['http://127.0.0.1:8081']

    rep = _load_rep()

    jobs = [ {"type":"compute","size":round(random.uniform(0.05,0.5),3),"latency_ms":random.randint(300,1500)} for _ in range(args.jobs) ]

    for job in jobs:
        cand = micro_auction(args.hosts, job, rep)
        if not cand:
            print("[broker] no candidate hosts")
            continue
        ok, res, chosen = False, None, None
        for _, host, quote in cand:
            chosen = host
            ok, res = dispatch(host, job, t_activate_s=args.t_activate_s)
            print(f"[broker] dispatch job -> {host} quote={quote} ok={ok}")
            if ok:
                # reward: reduce misses if any
                rep.setdefault(host, {"misses":0, "hits":0})
                rep[host]["hits"] += 1
                break
            else:
                rep.setdefault(host, {"misses":0, "hits":0})
                rep[host]["misses"] += 1
        if res:
            print(json.dumps(res, indent=2))
        _save_rep(rep)

if __name__ == "__main__":
    main()
