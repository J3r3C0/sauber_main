#!/usr/bin/env python3
"""Key utilities for Offgrid-Net v0.2 (PyNaCl required)

Generates and loads:
- Ed25519 Signing/Verify keys (receipts, identity)
- X25519 Private/Public keys (ECDH for E2EE)
"""
import json, base64, os
from pathlib import Path
from nacl import signing, public

def b64e(b: bytes) -> str:
    return base64.b64encode(b).decode()

def b64d(s: str) -> bytes:
    return base64.b64decode(s.encode())

def generate_keys(out_dir: str = "./keys", node_id: str = "node-A"):
    p = Path(out_dir); p.mkdir(parents=True, exist_ok=True)
    # Ed25519
    sk = signing.SigningKey.generate()
    vk = sk.verify_key
    # X25519
    xsk = public.PrivateKey.generate()
    xpk = xsk.public_key

    bundle = {
        "node_id": node_id,
        "ed25519": {
            "signing_key": b64e(bytes(sk)),
            "verify_key": b64e(bytes(vk)),
        },
        "x25519": {
            "private_key": b64e(bytes(xsk)),
            "public_key": b64e(bytes(xpk)),
        }
    }
    (p / f"{node_id}.json").write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    print(f"[keys] wrote {p / (node_id + '.json')}")

def load_keys(path: str):
    obj = json.loads(Path(path).read_text(encoding="utf-8"))
    return obj

if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--out_dir", default="./keys")
    ap.add_argument("--node_id", default="node-A")
    args = ap.parse_args()
    generate_keys(args.out_dir, args.node_id)
