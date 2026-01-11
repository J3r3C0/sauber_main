import requests
import json
import time
import hmac
import hashlib
import os
import sys
import base64
from typing import Optional, List, Dict

# Standard imports for Offgrid Logic
from .identity import CoreIdentity

class OffgridMemoryClient:
    """
    E2EE-enabled HTTP client for Offgrid memory and quorum services.
    Implements Offgrid v0.2+ Cryptography and v0.15+ Quorum.
    """
    
    def __init__(self, broker_url: str, hosts: List[str], auth_key: str, identity: CoreIdentity):
        self.broker_url = broker_url.rstrip('/')
        self.hosts = hosts
        self.auth_key = auth_key
        self.identity = identity
        self.session = requests.Session()
        self.host_keys_cache: Dict[str, str] = {} # host_url -> x25519_public_key_b64

    def _get_host_public_key(self, host_url: str) -> Optional[str]:
        """Fetch X25519 public key from the host."""
        if host_url in self.host_keys_cache:
            return self.host_keys_cache[host_url]
        
        try:
            resp = self.session.get(f"{host_url.rstrip('/')}/pubkeys", timeout=3)
            if resp.status_code == 200:
                pk = resp.json().get("x25519_public_key")
                if pk:
                    self.host_keys_cache[host_url] = pk
                    return pk
        except Exception as e:
            print(f"[mem_client] [WARN] Failed to fetch pubkey from {host_url}: {e}")
        return None

    def _encrypt_for_host(self, data_bytes: bytes, host_url: str) -> Optional[dict]:
        """Encrypts data for a specific host using E2EE."""
        peer_pk_b64 = self._get_host_public_key(host_url)
        if not peer_pk_b64:
            return None
            
        try:
            # We import the logic from offgrid if possible, or use nacl directly
            from nacl import public, bindings
            
            # 1. Derive shared secret (X25519)
            peer_pk = public.PublicKey(base64.b64decode(peer_pk_b64))
            shared = bindings.crypto_scalarmult(bytes(self.identity.private_key), bytes(peer_pk))
            
            # 2. Simple KDF (matching Offgrid encrypt_real.py)
            aead_key = hashlib.blake2b(shared + b"offgrid-net" + b"e2ee", digest_size=32).digest()
            
            # 3. Encrypt (XChaCha20)
            nonce = os.urandom(bindings.crypto_aead_xchacha20poly1305_ietf_NPUBBYTES)
            aad = f"{self.identity.node_id}:{int(time.time())}".encode()
            ct = bindings.crypto_aead_xchacha20poly1305_ietf_encrypt(data_bytes, aad, nonce, aead_key)
            
            return {
                "nonce": base64.b64encode(nonce).decode(),
                "ciphertext": base64.b64encode(ct).decode(),
                "aad": base64.b64encode(aad).decode()
            }
        except Exception as e:
            print(f"[mem_client] [ERROR] Encryption failed for {host_url}: {e}")
            return None

    def _sign(self, payload: dict) -> dict:
        """Sign payload with HMAC-SHA256 (standard Offgrid Broker auth)."""
        payload['timestamp'] = time.time()
        payload_str = json.dumps(payload, sort_keys=True)
        sig = hmac.new(
            self.auth_key.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        payload['signature'] = sig
        return payload

    def store_with_quorum(self, key: str, data: dict, etype: int = 2, required_acks: float = 1.0) -> Optional[str]:
        """
        Encrypts and stores data on hosts, then registers quorum on broker.
        
        Args:
            key: Unique identifier for the data
            data: Data dictionary to store
            etype: Event type (semantic type from event_types.py)
            required_acks: Quorum threshold
        """
        data_bytes = json.dumps(data).encode('utf-8')
        meta = {
            "key": key, 
            "type": "core_archive", 
            "encrypted": True, 
            "owner": self.identity.node_id,
            "etype": etype
        }
        
        # 1. Register Quorum Intent on Broker
        try:
            self.session.post(
                f"{self.broker_url}/quorum/create",
                json=self._sign({
                    "id": key,
                    "kind": "upload",
                    "required": required_acks,
                    "meta": meta
                }),
                timeout=5
            )
        except Exception as e:
            print(f"[mem_client] [WARN] Failed to create quorum: {e}")

        # 2. Encrypt and Ingest into Hosts
        success_count = 0
        last_eid = None
        
        for host in self.hosts:
            host_url = host.rstrip('/')
            
            # E2EE: Encrypt data for this specific host
            encrypted_blob = self._encrypt_for_host(data_bytes, host_url)
            if not encrypted_blob:
                continue
                
            payload_bytes = json.dumps(encrypted_blob).encode('utf-8')
            
            try:
                resp = self.session.post(
                    f"{host_url}/memory/ingest",
                    data=payload_bytes,
                    headers={
                        "X-Meta": json.dumps(meta),
                        "X-Score": "1.0",
                        "X-Type": str(etype)  # Use semantic etype
                    },
                    timeout=5
                )
                if resp.status_code == 200:
                    eid = resp.json()['eid']
                    last_eid = eid
                    success_count += 1
                    
                    # 3. Add Ack to Quorum
                    try:
                        self.session.post(
                            f"{self.broker_url}/quorum/ack",
                            json=self._sign({
                                "id": key,
                                "kind": "upload",
                                "node_id": host
                            }),
                            timeout=2
                        )
                    except:
                        pass
            except Exception:
                continue
                
        return last_eid if success_count > 0 else None

    def get_quorum_status(self, key: str) -> Optional[dict]:
        try:
            resp = self.session.get(f"{self.broker_url}/quorum/status/upload/{key}", timeout=5)
            if resp.status_code == 200:
                return resp.json()
        except:
            pass
        return None

    def fetch_and_decrypt(self, key: str) -> Optional[dict]:
        """
        Stub for fetching encrypted data and decrypting it.
        In a proper mesh, we'd query multiple hosts.
        """
        # 1. Query hosts for events with this key
        for host in self.hosts:
            try:
                # Naive query: find most recent for this key in meta
                resp = self.session.get(f"{host.rstrip('/')}/memory/query", params={"limit": 10}, timeout=5)
                if resp.status_code == 200:
                    events = resp.json().get('events', [])
                    for ev in events:
                        if ev['meta'].get('key') == key:
                            # 2. Fetch the actual blob (it might be in 'pref' if large)
                            blob_bytes = None
                            if ev.get('pref'):
                                # Large blob handling needed here (fetch chunk)
                                pass
                            
                            # For now, we assume it's small and in the ingest body 
                            # (Wait, ingest stores body. In query, how do we get the body?)
                            # Offgrid's query_endpoint returns meta/pref/score. 
                            # To get data, we need /memory/get/{eid}
                            
                            resp_data = self.session.get(f"{host.rstrip('/')}/memory/get/{ev['eid']}", timeout=5)
                            if resp_data.status_code == 200:
                                # This is the encrypted blob JSON
                                encrypted_blob = resp_data.json()
                                # 3. Decrypt
                                decrypted_bytes = self.identity.decrypt(
                                    encrypted_blob, 
                                    self._get_host_public_key(host)
                                )
                                return json.loads(decrypted_bytes)
            except Exception as e:
                print(f"[mem_client] [WARN] Fetch failed from {host}: {e}")
                continue
        return None
