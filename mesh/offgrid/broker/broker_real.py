#!/usr/bin/env python3
import json, time, argparse
from pathlib import Path
from urllib.request import urlopen, Request
REPUTATION_FILE = Path("./_reputation.json")

def load_rep():
    if REPUTATION_FILE.exists():
        try:
            return json.loads(REPUTATION_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_rep(rep):
    REPUTATION_FILE.write_text(json.dumps(rep, indent=2), encoding="utf-8")

def ping_status(ep: str, timeout=2.0) -> bool:
    url = ep.rstrip("/") + "/status"
    try:
        with urlopen(Request(url, headers={"Accept":"application/json"}), timeout=timeout) as r:
            return r.status == 200
    except Exception:
        return False

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--discovery", default="discovery/mesh_hosts.json")
    ap.add_argument("--interval", type=float, default=4.0)
    args = ap.parse_args()

    disc = Path(args.discovery)
    rep = load_rep()
    print("[broker] running (reputation manager)")
    while True:
        hosts = []
        if disc.exists():
            try:
                data = json.loads(disc.read_text(encoding="utf-8"))
                hosts = data.get("hosts", [])
            except Exception:
                hosts = []
        if not hosts:
            print("[broker] no candidate hosts")
            time.sleep(args.interval); continue

        chosen = []
        for h in hosts:
            ep = h.get("endpoint")
            ok = ping_status(ep)
            key = h.get("node") + "|" + ep
            cur = rep.get(key, 0.0)
            rep[key] = max(0.0, min(1.0, cur + (0.05 if ok else -0.05)))
            if ok:
                chosen.append((rep[key], ep))
        save_rep(rep)
        chosen.sort(reverse=True)
        if chosen:
            topline = ", ".join([f"{ep} ({score:.2f})" for score, ep in chosen[:3]])
            print(f"[broker] candidates: {topline}")
        else:
            print("[broker] all candidates failing ping")
        time.sleep(args.interval)

if __name__ == "__main__":
    main()
