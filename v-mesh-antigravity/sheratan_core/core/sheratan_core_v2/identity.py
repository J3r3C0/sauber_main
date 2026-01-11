from __future__ import annotations
import json
import base64
import os
from pathlib import Path
from nacl import signing, public
from typing import Optional, Dict

class CoreIdentity:
    """
    Manages the cryptographic identity of Sheratan Core.
    Follows Offgrid-Net v0.2 standards (PyNaCl).
    """
    
    def __init__(self, keys_path: str = "keys/core-identity.json"):
        self.keys_path = Path(keys_path)
        self.node_id: str = "core-v2"
        self.signing_key: Optional[signing.SigningKey] = None
        self.verify_key: Optional[signing.VerifyKey] = None
        self.private_key: Optional[public.PrivateKey] = None
        self.public_key: Optional[public.PublicKey] = None
        
        self._load_or_generate()

    def _load_or_generate(self):
        if self.keys_path.exists():
            try:
                data = json.loads(self.keys_path.read_text(encoding="utf-8"))
                self.node_id = data.get("node_id", "core-v2")
                
                # Ed25519
                sk_bytes = base64.b64decode(data["ed25519"]["signing_key"])
                self.signing_key = signing.SigningKey(sk_bytes)
                self.verify_key = self.signing_key.verify_key
                
                # X25519
                pk_bytes = base64.b64decode(data["x25519"]["private_key"])
                self.private_key = public.PrivateKey(pk_bytes)
                self.public_key = self.private_key.public_key
                
                print(f"[identity] Loaded Core identity: {self.node_id}")
                return
            except Exception as e:
                print(f"[identity] [WARN] Failed to load keys, regenerating: {e}")

        # Generate new keys
        self.signing_key = signing.SigningKey.generate()
        self.verify_key = self.signing_key.verify_key
        self.private_key = public.PrivateKey.generate()
        self.public_key = self.private_key.public_key
        
        self._save()
        print(f"[identity] Generated new Core identity: {self.node_id}")

    def _save(self):
        self.keys_path.parent.mkdir(parents=True, exist_ok=True)
        bundle = {
            "node_id": self.node_id,
            "ed25519": {
                "signing_key": base64.b64encode(bytes(self.signing_key)).decode(),
                "verify_key": base64.b64encode(bytes(self.verify_key)).decode(),
            },
            "x25519": {
                "private_key": base64.b64encode(bytes(self.private_key)).decode(),
                "public_key": base64.b64encode(bytes(self.public_key)).decode(),
            }
        }
        self.keys_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")

    def get_public_bundle(self) -> Dict[str, str]:
        """Returns public keys in a format expected by Offgrid nodes."""
        return {
            "node_id": self.node_id,
            "ed25519_verify_key": base64.b64encode(bytes(self.verify_key)).decode(),
            "x25519_public_key": base64.b64encode(bytes(self.public_key)).decode(),
        }

    def sign(self, message: bytes) -> bytes:
        return self.signing_key.sign(message).signature

    def decrypt(self, ciphertext_blob: dict, sender_public_key_b64: str) -> bytes:
        """Decrypts a blob from a remote peer."""
        from storage.encrypt_real import decrypt_xchacha, derive_shared_key
        
        peer_pk = public.PublicKey(base64.b64decode(sender_public_key_b64))
        shared_key = derive_shared_key(self.private_key, peer_pk)
        
        return decrypt_xchacha(
            ciphertext_blob["nonce"],
            ciphertext_blob["ciphertext"],
            shared_key
        )
