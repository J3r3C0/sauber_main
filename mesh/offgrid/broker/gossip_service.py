#!/usr/bin/env python3
"""Gossip v0.9
- Pull/Push von Ledger-Blöcken (DAG) und Wallet-Balances (Snapshots) zwischen Peers.
- Simple HTTP: nutzt vorhandene Host-Daemon-Endpunkte oder eigenständigen Mini-Server.
- Ziel: eventual consistency ohne globalen Konsens.
"""
import json, time, threading, argparse
from pathlib import Path
from http.server import BaseHTTPRequestHandler, HTTPServer

LEDGER_DIR = Path("./_ledger")
BAL_FILE = Path("./_balances.json")
REP_FILE = Path("./_reputation.json")
TX_POOL = Path("./_txpool.json")

def list_blocks():
    return [p.name for p in sorted(LEDGER_DIR.glob("*.json"))]

def read_block(name):
    p = LEDGER_DIR / name
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8"))
    return None

def append_block(block: dict):
    p = LEDGER_DIR / f"{block['ts']}_{block['hash']}.json"
    if not p.exists():
        p.write_text(json.dumps(block, indent=2), encoding="utf-8")
        return True
    return False

def load_balances():
    if BAL_FILE.exists():
        return json.loads(BAL_FILE.read_text(encoding="utf-8"))
    return {"system":0.0}

def save_balances(obj):
    BAL_FILE.write_text(json.dumps(obj, indent=2), encoding="utf-8")

def merge_balances(remote):
    local = load_balances()
    # strategy: element-wise max by timestamp not available -> use sum on keys except system?
    # For demo: take max for each account to avoid double-credit; in real system need transfer logs
    merged = dict(local)
    for k,v in remote.items():
        if k not in merged:
            merged[k] = v
        else:
            merged[k] = max(merged[k], v)
    save_balances(merged)
    return merged

def load_rep():
    if REP_FILE.exists():
        return json.loads(REP_FILE.read_text(encoding="utf-8"))
    return {}

def save_rep(obj):
    REP_FILE.write_text(json.dumps(obj, indent=2), encoding="utf-8")

def merge_rep(remote):
    local = load_rep()
    for host, rv in remote.items():
        lv = local.get(host, {"hits":0,"misses":0})
        local[host] = {"hits": max(lv.get("hits",0), rv.get("hits",0)),
                       "misses": max(lv.get("misses",0), rv.get("misses",0))}
    save_rep(local)
    return local

class H(BaseHTTPRequestHandler):
    def _send(self, code, obj):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())

    def do_GET(self):
        if self.path.startswith("/gossip/blocks"):
            self._send(200, {"blocks": list_blocks()})
        elif self.path.startswith("/gossip/block?"):
            import urllib.parse as up
            q = up.parse_qs(up.urlparse(self.path).query)
            name = q.get("name",[""])[0]
            blk = read_block(name)
            if blk: self._send(200, blk)
            else: self._send(404, {"error":"not found"})
        elif self.path.startswith("/gossip/balances"):
            self._send(200, load_balances())
        elif self.path.startswith("/gossip/rep"):
            self._send(200, load_rep())
        elif self.path.startswith("/gossip/tx_pool"):
            obj = json.loads(TX_POOL.read_text(encoding="utf-8")) if TX_POOL.exists() else []
            self._send(200, obj)
        else:
            self._send(404, {"error":"not found"})

    def do_POST(self):
        ln = int(self.headers.get("Content-Length","0") or "0")
        body = self.rfile.read(ln) if ln>0 else b"{}"
        try:
            data = json.loads(body.decode())
        except Exception:
            data = {}
        if self.path == "/gossip/append_block":
            ok = append_block(data)
            self._send(200, {"ok": ok})
        elif self.path == "/gossip/merge_balances":
            merged = merge_balances(data)
            self._send(200, merged)
        elif self.path == "/gossip/merge_rep":
            merged = merge_rep(data)
            self._send(200, merged)
        elif self.path == "/gossip/tx_witness":
            # append/merge tx with witness
            pool = json.loads(TX_POOL.read_text(encoding="utf-8")) if TX_POOL.exists() else []
            found = False
            for i,t in enumerate(pool):
                if t.get("id") == data.get("id"):
                    # merge witnesses
                    wset = { (w.get("verify_key"), w.get("signature")) for w in t.get("witnesses",[]) }
                    for w in data.get("witnesses",[]):
                        tup = (w.get("verify_key"), w.get("signature"))
                        if tup not in wset:
                            t.setdefault("witnesses", []).append(w)
                            wset.add(tup)
                    pool[i] = t
                    found = True
                    break
            if not found:
                pool.append(data)
            TX_POOL.write_text(json.dumps(pool, indent=2), encoding="utf-8")
            self._send(200, {"ok": True})
        else:
            self._send(404, {"error":"not found"})

def run_server(port=8091):
    srv = HTTPServer(("0.0.0.0", port), H)
    print(f"[gossip] serving on :{port}")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass

def pull_from_peer(peer: str):
    import urllib.request as u
    import json
    # blocks list
    try:
        bl = json.loads(u.urlopen(f"{peer}/gossip/blocks", timeout=5).read().decode()).get("blocks",[])
    except Exception:
        bl = []
    for name in bl:
        try:
            blk = json.loads(u.urlopen(f"{peer}/gossip/block?name={name}", timeout=5).read().decode())
            append_block(blk)
        except Exception:
            pass
    # balances
    try:
        rem_bal = json.loads(u.urlopen(f"{peer}/gossip/balances", timeout=5).read().decode())
        merge_balances(rem_bal)
    except Exception:
        pass
    # reputation
    try:
        rem_rep = json.loads(u.urlopen(f"{peer}/gossip/rep", timeout=5).read().decode())
        merge_rep(rem_rep)
    except Exception:
        pass

def main():
    import argparse, threading, time, json
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8091)
    ap.add_argument("--peers", nargs="+", default=[])
    ap.add_argument("--interval", type=int, default=30)
    args = ap.parse_args()

    t = threading.Thread(target=run_server, args=(args.port,), daemon=True)
    t.start()
    print("[gossip] peers:", args.peers)
    try:
        while True:
            for p in args.peers:
                pull_from_peer(p)
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
