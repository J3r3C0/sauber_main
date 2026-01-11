#!/usr/bin/env python3

import json, argparse, threading, time
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from receipts import ReceiptStore
from nacl import signing, public
import json, base64
from pathlib import Path as _Path

import threading
STORE_SEM = threading.Semaphore(4)
STATE = {
    "node_id": "did:key:z-demo",
    "active": True,
    "min_oncall_percent": 10,
    "burst_percent_max": 60,
    "prices": {
        "per_gb_hour": 0.02,
        "per_mtoken_infer": 0.03,
        "per_gb_transfer": 0.005
    },
    "keys_path": "./keys/node-A.json",  # PyNaCl keys (Ed25519 + X25519)
    "receipts_dir": "./_receipts"
}

store = None

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, payload, ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.end_headers()
        if isinstance(payload, (dict, list)):
            self.wfile.write(json.dumps(payload).encode())
        elif isinstance(payload, (str, bytes)):
            self.wfile.write(payload if isinstance(payload, bytes) else payload.encode())
        else:
            self.wfile.write(json.dumps({"ok": True}).encode())

    def do_GET(self):
        u = urlparse(self.path)
        if u.path == "/quote":
            # simple quote based on size/type
            qs = parse_qs(u.query or "")
            typ = (qs.get("type", ["compute"])[0]).lower()
            size = float(qs.get("size", ["1"])[0])
            p = STATE["prices"]
            if typ == "compute":
                price = p["per_mtoken_infer"] * size
            elif typ == "storage":
                price = p["per_gb_hour"] * size
            elif typ == "transfer":
                price = p["per_gb_transfer"] * size
            else:
                price = 0.0
            self._send(200, {"type": typ, "size": size, "quote": price})
        elif u.path == "/receipts/export":
            batch = store.export_batch(limit=500)
            self._send(200, batch)
        elif u.path == "/pubkeys":
            # publish verify + x25519 public
            keys_obj = json.loads(_Path(STATE["keys_path"]).read_text())
            out = {"node_id": STATE["node_id"], "ed25519_verify_key": keys_obj["ed25519"]["verify_key"], "x25519_public_key": keys_obj["x25519"]["public_key"]}
            self._send(200, out)
        elif u.path == "/mesh":
            # serve local mesh metrics if present
            from pathlib import Path as __P
            import json as __J
            mf = __P("./mesh/last_metrics.json")
            if mf.exists():
                self._send(200, __J.loads(mf.read_text(encoding="utf-8")))
            else:
                self._send(200, {"proto":"none","neighbors":[],"routes":[],"health":{"interfaces_up":0,"mesh_ok":False}})
        elif u.path == "/store":
            # Store encrypted shard: {"asset_id","index","data_b64"}
            import base64, os
            if not STORE_SEM.acquire(blocking=False):
                self.send_response(503)
                self.send_header("Retry-After", "2")
                self.send_header("Content-Type","application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error":"busy"}).encode()); return
            try:
                asset_id = data.get("asset_id")
                index = int(data.get("index", -1))
                b64 = data.get("data_b64","")
                assert asset_id and index >= 0 and b64
                raw = base64.b64decode(b64.encode())
                shard_dir = Path("./_shards")/asset_id
                shard_dir.mkdir(parents=True, exist_ok=True)
                (shard_dir/f"shard_{index:02d}.bin").write_bytes(raw)
                self._send(200, {"ok": True, "stored": index})
            except Exception as e:
                self._send(400, {"error": str(e)})
            finally:
                STORE_SEM.release()
        elif u.path == "/fetch":
            # Query: ?asset_id=...&index=..
            qs = parse_qs(u.query or "")
            asset_id = (qs.get("asset_id", [""])[0])
            try:
                index = int(qs.get("index", ["-1"])[0])
            except Exception:
                index = -1
            if not asset_id or index < 0:
                self._send(400, {"error":"bad params"})
                return
            p = Path("./_shards")/asset_id/f"shard_{index:02d}.bin"
            if not p.exists():
                self._send(404, {"error":"not found"})
                return
            import base64
            b64 = base64.b64encode(p.read_bytes()).decode()
            self._send(200, {"asset_id": asset_id, "index": index, "data_b64": b64})
        elif u.path == "/announce":
            info = {
                "node_id": STATE["node_id"],
                "active": STATE["active"],
                "min_oncall_percent": STATE["min_oncall_percent"],
                "burst_percent_max": STATE["burst_percent_max"],
                "prices": STATE["prices"],
            }
            self._send(200, info)
        else:
            self._send(404, {"error": "not found"})

    def do_POST(self):
        u = urlparse(self.path)
        ln = int(self.headers.get("Content-Length", "0") or "0")
        try:
            raw_body = self.rfile.read(ln) if ln > 0 else b"{}"
            data = json.loads(raw_body.decode() or "{}")
        except Exception:
            data = {}
        
        # /hs responder
        if u.path == '/hs':
            from crypto.session import Identity, responder_handshake
            keys_p = Path(STATE.get('keys_path', './keys/node-A.json'))
            if not keys_p.exists():
                self._send(404, {"error": "keys not found"})
                return
            kd = json.loads(keys_p.read_text(encoding="utf-8"))
            msg2, key, _ = responder_handshake(Identity.from_json(kd), data)
            self._send(200, {"ok": True, "msg2": msg2})
            return
        if u.path == "/toggle":
            STATE["active"] = bool(data.get("active", True))
            self._send(200, {"active": STATE["active"]})
        elif u.path == "/run":
            # simulate work and create receipt
            job_id = data.get("job_id", f"job-{int(time.time()*1000)}")
            metrics = data.get("metrics", {"compute_tokens_m": 0.1, "latency_ms": 1000})
            time.sleep(min(1.0, (metrics.get("latency_ms", 200)/1000.0)))  # simulate
            rec = store.create_usage_receipt(STATE["node_id"], job_id, metrics)
            self._send(200, {"ok": True, "receipt": rec})
        elif u.path == "/pubkeys":
            # publish verify + x25519 public
            keys_obj = json.loads(_Path(STATE["keys_path"]).read_text())
            out = {"node_id": STATE["node_id"], "ed25519_verify_key": keys_obj["ed25519"]["verify_key"], "x25519_public_key": keys_obj["x25519"]["public_key"]}
            self._send(200, out)
        elif u.path == "/mesh":
            # serve local mesh metrics if present
            from pathlib import Path as __P
            import json as __J
            mf = __P("./mesh/last_metrics.json")
            if mf.exists():
                self._send(200, __J.loads(mf.read_text(encoding="utf-8")))
            else:
                self._send(200, {"proto":"none","neighbors":[],"routes":[],"health":{"interfaces_up":0,"mesh_ok":False}})
        elif u.path == "/store":
            # Store encrypted shard: {"asset_id","index","data_b64"}
            import base64, os
            if not STORE_SEM.acquire(blocking=False):
                self.send_response(503)
                self.send_header("Retry-After", "2")
                self.send_header("Content-Type","application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"error":"busy"}).encode()); return
            try:
                asset_id = data.get("asset_id")
                index = int(data.get("index", -1))
                b64 = data.get("data_b64","")
                assert asset_id and index >= 0 and b64
                raw = base64.b64decode(b64.encode())
                shard_dir = Path("./_shards")/asset_id
                shard_dir.mkdir(parents=True, exist_ok=True)
                (shard_dir/f"shard_{index:02d}.bin").write_bytes(raw)
                self._send(200, {"ok": True, "stored": index})
            except Exception as e:
                self._send(400, {"error": str(e)})
            finally:
                STORE_SEM.release()
        elif u.path == "/fetch":
            # Query: ?asset_id=...&index=..
            qs = parse_qs(u.query or "")
            asset_id = (qs.get("asset_id", [""])[0])
            try:
                index = int(qs.get("index", ["-1"])[0])
            except Exception:
                index = -1
            if not asset_id or index < 0:
                self._send(400, {"error":"bad params"})
                return
            p = Path("./_shards")/asset_id/f"shard_{index:02d}.bin"
            if not p.exists():
                self._send(404, {"error":"not found"})
                return
            import base64
            b64 = base64.b64encode(p.read_bytes()).decode()
            self._send(200, {"asset_id": asset_id, "index": index, "data_b64": b64})
        elif u.path == "/announce":
            # allow runtime updates: prices, oncall
            for k in ("min_oncall_percent","burst_percent_max"):
                if k in data: STATE[k] = int(data[k])
            if "prices" in data: STATE["prices"].update(data["prices"])
            self._send(200, {"ok": True, "state": {
                "active": STATE["active"],
                "min_oncall_percent": STATE["min_oncall_percent"],
                "burst_percent_max": STATE["burst_percent_max"],
                "prices": STATE["prices"],
            }})
        else:
            self._send(404, {"error": "not found"})

def main():
    global store
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8081)
    ap.add_argument("--receipts_dir", type=str, default=STATE["receipts_dir"])
    ap.add_argument("--node_id", type=str, default=STATE["node_id"])
    args = ap.parse_args()
    STATE["node_id"] = args.node_id
    STATE["receipts_dir"] = args.receipts_dir
    Path(args.receipts_dir).mkdir(parents=True, exist_ok=True)
    keys_obj = json.loads(_Path(STATE["keys_path"]).read_text())
    ed_sk = signing.SigningKey(base64.b64decode(keys_obj["ed25519"]["signing_key"]))
    store = ReceiptStore(args.receipts_dir, ed_sk, cluster_id="cluster-local")
    xsk = public.PrivateKey(base64.b64decode(keys_obj["x25519"]["private_key"]))
    xpk_b64 = keys_obj["x25519"]["public_key"]

    print(f"[host-daemon] node_id={STATE['node_id']} port={args.port} active={STATE['active']}")
    HTTPServer(("0.0.0.0", args.port), Handler).serve_forever()

if __name__ == "__main__":
    main()
