# (same as in monolithic 0.16-alpha) — copy into your tree if not present
from nacl import public, signing, secret, utils
import base64, json, hmac, hashlib, time
from dataclasses import dataclass

def hkdf_sha256(ikm: bytes, salt: bytes = b"", info: bytes = b"", length: int = 32) -> bytes:
    if not salt: salt = b"\x00" * 32
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    t=b""; okm=b""; blk=0
    while len(okm)<length:
        blk+=1; t = hmac.new(prk, t+info+bytes([blk]), hashlib.sha256).digest(); okm+=t
    return okm[:length]

@dataclass
class Identity:
    ed25519_sign: signing.SigningKey
    ed25519_verify: signing.VerifyKey
    x25519_static: public.PrivateKey
    x25519_public: public.PublicKey
    @staticmethod
    def from_json(d: dict) -> "Identity":
        ed_sk = signing.SigningKey(base64.b64decode(d["ed25519"]["signing_key"]))
        ed_vk = ed_sk.verify_key
        x_sk = public.PrivateKey(base64.b64decode(d["x25519"]["private_key"]))
        x_pk = x_sk.public_key
        return Identity(ed_sk, ed_vk, x_sk, x_pk)

class Session:
    def __init__(self, key: bytes, peer_endpoint: str):
        self.key = key
        self.peer_endpoint = peer_endpoint
        self.box = secret.SecretBox(key)
    
    def seal(self, payload: bytes, aad: dict = None) -> str:
        nonce = utils.random(24)
        # simplistic AAD integration in JSON envelope
        ct = self.box.encrypt(payload, nonce)
        env = {
            "ct_b64": base64.b64encode(ct.ciphertext).decode(),
            "nonce_b64": base64.b64encode(ct.nonce).decode(),
            "ts": int(time.time()*1000)
        }
        if aad: env["aad"] = aad
        return base64.b64encode(json.dumps(env).encode()).decode()

    def open(self, env_b64: str) -> bytes:
        env = json.loads(base64.b64decode(env_b64).decode())
        ct = base64.b64decode(env["ct_b64"])
        nonce = base64.b64decode(env["nonce_b64"])
        return self.box.decrypt(ct, nonce)

def initiator_handshake(id: Identity, peer_xpk_b64: str):
    ephem = public.PrivateKey.generate()
    peer_xpk = public.PublicKey(base64.b64decode(peer_xpk_b64))
    # DH(ephem, static)
    shared = public.Box(ephem, peer_xpk).shared_key()
    # Simplified Noise: msg1 = ephem_pub
    msg1 = {
        "e_b64": base64.b64encode(bytes(ephem.public_key)).decode(),
        "ts": int(time.time()*1000)
    }
    # key material
    key = hkdf_sha256(shared, info=b"offgrid-noise-v1")
    return msg1, key

def responder_handshake(id: Identity, msg1: dict):
    ephem_pub = public.PublicKey(base64.b64decode(msg1["e_b64"]))
    # DH(static, ephem)
    shared = public.Box(id.x25519_static, ephem_pub).shared_key()
    # msg2 = ack
    msg2 = {"ok": True, "ts": int(time.time()*1000)}
    key = hkdf_sha256(shared, info=b"offgrid-noise-v1")
    return msg2, key, None # peer_ed not used in this simplest version

def session_from_key(key: bytes, endpoint: str) -> Session:
    return Session(key, endpoint)
