import json, time, os, base64, random
from pathlib import Path
from nacl import signing

SCHEMA_VERSION = "0.2"

def b64e(b: bytes) -> str:
    return base64.b64encode(b).decode()

class ReceiptStore:
    def __init__(self, base_dir: str, ed25519_signing_key: signing.SigningKey, cluster_id: str = "cluster-local"):
        self.base = Path(base_dir)
        self.base.mkdir(parents=True, exist_ok=True)
        self.sk = ed25519_signing_key
        self.vk_b64 = b64e(bytes(self.sk.verify_key))
        self.cluster_id = cluster_id

    def create_usage_receipt(self, node_id: str, job_id: str, resource_type: str, units: float, metrics: dict) -> dict:
        rec = {
            "version": SCHEMA_VERSION,
            "cluster_id": self.cluster_id,
            "ts": int(time.time() * 1000),
            "node_id": node_id,
            "job_id": job_id,
            "resource_type": resource_type,
            "units": units,
            "metrics": metrics,
            "proofs": {},
            "cids": [],
            "nonce": random.randint(0, 2**31-1),
            "sig_algo": "Ed25519",
            "verify_key": self.vk_b64,
        }
        payload = json.dumps(rec, sort_keys=True).encode()
        sig = self.sk.sign(payload).signature
        rec["sig"] = b64e(sig)
        out = self.base / f"{rec['ts']}_{job_id}.json"
        out.write_text(json.dumps(rec, indent=2), encoding="utf-8")
        return rec

    def export_batch(self, limit: int = 1000) -> dict:
        files = sorted(self.base.glob("*.json"))[:limit]
        items = [json.loads(p.read_text(encoding="utf-8")) for p in files]
        # Merkle root
        import hashlib
        def h(b): return hashlib.sha256(b).hexdigest().encode()
        leaves = [h(json.dumps(it, sort_keys=True).encode()) for it in items]
        if not leaves:
            root = hashlib.sha256(b"empty").hexdigest()
        else:
            nodes = leaves[:]
            while len(nodes) > 1:
                nxt = []
                for a, b in zip(nodes[0::2], nodes[1::2]):
                    nxt.append(h(a + b))
                if len(nodes) % 2 == 1:
                    nxt.append(nodes[-1])
                nodes = nxt
            root = nodes[0].decode()
        return {
            "version": SCHEMA_VERSION,
            "cluster_id": self.cluster_id,
            "count": len(items),
            "root": root,
            "items": items,
        }
