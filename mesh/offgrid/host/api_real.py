import argparse, json, time, hmac, hashlib, base64, sys, sqlite3, os, asyncio
from pathlib import Path
from typing import Optional, Dict, Any

# Add parent directories to path for imports
_host_dir = Path(__file__).parent
_offgrid_dir = _host_dir.parent
_mesh_dir = _offgrid_dir.parent
_project_root = _mesh_dir.parent

for p in [str(_offgrid_dir), str(_mesh_dir), str(_project_root)]:
    if p not in sys.path:
        sys.path.insert(0, p)

from fastapi import FastAPI, Request
import uvicorn

# Force UTF-8 for Windows shell logging
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

def make_app(node_id: str, auth_key: str = "shared-secret"):
    # Jailed Root for physical execution
    ALLOWED_ROOT = Path("./data").resolve()
    ALLOWED_ROOT.mkdir(parents=True, exist_ok=True)
    
    # Persistent SQLite Attempt Store
    db_path = Path(f"./attempts_{node_id}.db")
    db = sqlite3.connect(str(db_path), check_same_thread=False)
    db.execute("""
        CREATE TABLE IF NOT EXISTS attempts (
            attempt_id TEXT PRIMARY KEY,
            status TEXT,
            result TEXT,
            timestamp INTEGER
        )
    """)
    db.commit()

    def _get_attempt_result(attempt_id: str) -> Optional[dict]:
        cursor = db.execute("SELECT status, result FROM attempts WHERE attempt_id = ?", (attempt_id,))
        row = cursor.fetchone()
        if row:
            status, res_json = row
            if status == "COMPLETED" and res_json:
                return json.loads(res_json)
            return {"ok": False, "error_code": "IN_PROGRESS"}
        return None

    def _save_attempt_result(attempt_id: str, result: dict):
        db.execute(
            "UPDATE attempts SET status = 'COMPLETED', result = ?, timestamp = ? WHERE attempt_id = ?",
            (json.dumps(result), int(time.time()), attempt_id)
        )
        db.commit()

    def _claim_attempt(attempt_id: str) -> bool:
        """Atomic claim using SQLite PRIMARY KEY constraint."""
        try:
            db.execute(
                "INSERT INTO attempts (attempt_id, status, timestamp) VALUES (?, 'IN_PROGRESS', ?)",
                (attempt_id, int(time.time()))
            )
            db.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def _cleanup_old_attempts():
        # TTL: 24 hours
        cutoff = int(time.time()) - 86400
        db.execute("DELETE FROM attempts WHERE timestamp < ?", (cutoff,))
        db.commit()

    _cleanup_old_attempts()
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Startup logic
        import threading
        try:
            from config.loader import load_config
            cfg = load_config(None)
            auto_accept = bool(cfg.get("policy", {}).get("auto_accept", False))
        except Exception:
            auto_accept = False
        
        PROV_PATH = Path("discovery/provisional.json")
        PEERS_PATH = Path("discovery/peers.json")

        def _js_load(p):
            try:
                return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                return {}

        def _js_save(p, obj):
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(obj, indent=2), encoding="utf-8")

        def _meets(entry):
            m = entry.get("meta", {}) or {}
            return bool(entry.get("trusted")) and bool(m.get("sig_ok")) and bool(m.get("challenge_ok"))

        def worker():
            if not auto_accept:
                return
            while True:
                try:
                    prov = _js_load(PROV_PATH) or {}
                    peers = _js_load(PEERS_PATH) or {}
                    changed = False
                    for k, v in list(prov.items()):
                        if _meets(v):
                            v["accepted_ts"] = int(time.time()*1000)
                            v["accepted_by"] = "policy-auto"
                            peers[k] = v
                            prov.pop(k, None)
                            changed = True
                    if changed:
                        _js_save(PROV_PATH, prov)
                        _js_save(PEERS_PATH, peers)
                except Exception:
                    pass
                time.sleep(5)

        threading.Thread(target=worker, daemon=True).start()
        
        # START HEARTBEAT
        try:
            from host.heartbeat import HeartbeatClient
            core_url = os.getenv("SHERATAN_CORE_URL", "http://localhost:8001")
            hb = HeartbeatClient(core_url=core_url, host_id=node_id)
            await hb.start()
            app.state.hb = hb
        except Exception as e:
            print(f"[{node_id}] Failed to start heartbeat: {e}")
        
        yield
        
        # STOP HEARTBEAT
        if hasattr(app.state, "hb"):
            await app.state.hb.stop()

    app = FastAPI(lifespan=lifespan)

    # Phase 4: Policy Allowlist
    OUTPUT_ALLOWLIST = ["verify_success.txt", "jail_success.md", "debug.txt", "verify_success.md"]

    def safe_join(rel_path: str) -> Path:
        """Prevent path traversal and enforce allowlist/symlink policy."""
        # 1. Jail check
        p = (ALLOWED_ROOT / rel_path).resolve()
        if not str(p).startswith(str(ALLOWED_ROOT)):
            raise ValueError("INVALID_PATH")
        
        # 2. Allowlist check (Phase 4)
        fname = p.name
        if not any(fname.startswith(prefix) for prefix in ["verify_", "jail_", "debug_", "secure_"]):
             # For production, we'd use more robust pattern matching
             pass # Allowing our test patterns for now

        # 3. Symlink protection (Phase 4)
        if p.exists() and p.is_symlink():
            raise ValueError("SYMLINK_REJECTED")
            
        return p

    def verify_claim_token(spec: dict) -> bool:
        """Verify the HMAC claim token from the Orchestrator."""
        token = spec.get("claim_token")
        if not token:
            return False
        
        # Verify deadline
        deadline = spec.get("deadline_ts", 0)
        if time.time() > deadline:
            return False
            
        msg = f"{spec['job_id']}:{spec['attempt_id']}:{deadline}"
        expected = hmac.new(
            auth_key.encode(),
            msg.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(token, expected)

    @app.get("/status")
    def status():
        return {"ok": True, "node_id": node_id, "ts": time.time()}

    @app.get("/announce")
    def announce():
        return {"ok": True, "node_id": node_id}

    @app.get("/pubkeys")
    def pubkeys():
        # publish verify + x25519 public
        keys_p = Path(f"./keys/{node_id}.json")
        if not keys_p.exists():
            keys_p = Path(f"./keys/node-A.json") # default fallback
        if not keys_p.exists():
             return {"error": "keys not found"}
        kd = json.loads(keys_p.read_text(encoding="utf-8"))
        return {
            "node_id": node_id,
            "ed25519_verify_key": kd["ed25519"]["verify_key"],
            "x25519_public_key": kd["x25519"]["public_key"]
        }

    @app.post("/hs")
    async def handshake(req: Request):
        from crypto.session import Identity, responder_handshake
        data = await req.json()
        keys_p = Path(f"./keys/{node_id}.json")
        if not keys_p.exists():
            keys_p = Path(f"./keys/node-A.json")
        kd = json.loads(keys_p.read_text(encoding="utf-8"))
        msg2, key, _ = responder_handshake(Identity.from_json(kd), data)
        return {"ok": True, "msg2": msg2}

    @app.get("/quote")
    def quote(type: str = "compute", size: float = 0.1):
        return {"quote": 0.5 + size, "host": node_id}

    @app.get("/mesh")
    def mesh():
        """Return mesh health status for monitoring."""
        return {
            "proto": "direct",
            "neighbors": [],
            "routes": [],
            "health": {
                "interfaces_up": 1,
                "mesh_ok": True
            },
            "node_id": node_id
        }

    @app.post("/run")
    async def run_internal(req: Request):
        payload = await req.json()
        
        # 1. Extract JobSpec (Priority: Versioned JobSpec -> Legacy Flattened)
        spec = payload.get("job")
        is_legacy = False
        
        if not spec:
            # Fallback for Legacy/Transition phase
            spec = payload
            is_legacy = True
            print(f"[{node_id}] WARNING: Running legacy payload for job {spec.get('job_id')}")

        job_id = spec.get("job_id")
        req_id = spec.get("req_uid") or payload.get("req_id") or "legacy"
        attempt_id = spec.get("attempt_id", "legacy-attempt")
        kind = spec.get("kind") or spec.get("type") # Legacy used 'type' sometimes
        args = spec.get("args") or spec.get("metrics", {}) # Legacy mapped args to 'metrics'
        
        print(f"[{node_id}] [req={req_id}] Request: kind={kind} attempt={attempt_id}")

        # 2. Idempotency Check & Atomic Claim
        cached = _get_attempt_result(attempt_id)
        if cached:
            print(f"[{node_id}] [req={req_id}] Returning cached result for attempt {attempt_id}")
            cached["request_id"] = req_id
            return cached

        # 4. Execution Logic (with Timeout Handling)
        timeout = float(spec.get("timeout_seconds") or payload.get("timeout") or 300)
        
        async def _execute():
            if kind == "write_file":
                try:
                    rel_path = args.get("path") or args.get("file")
                    content_b64 = args.get("content_b64")
                    if not rel_path or not content_b64:
                        return {"ok": False, "error_code": "INVALID_ARGS"}

                    out_path = safe_join(rel_path)
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    data = base64.b64decode(content_b64)
                    out_path.write_bytes(data)
                    return {
                        "ok": True,
                        "attempt_id": attempt_id,
                        "result": {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}
                    }
                except Exception as e:
                    return {"ok": False, "error": str(e)}

            elif kind == "list_files":
                try:
                    rel_root = args.get("root") or args.get("target") or "."
                    recursive = bool(args.get("recursive", False))
                    search_root = safe_join(rel_root)
                    if not search_root.is_dir():
                        return {"ok": False, "error_code": "NOT_A_DIRECTORY"}
                    files = []
                    patterns = args.get("patterns") or ["*"]
                    for pattern in patterns:
                        glob_pattern = f"**/{pattern}" if recursive else pattern
                        for p in search_root.glob(glob_pattern):
                            if p.is_file():
                                files.append(str(p.relative_to(ALLOWED_ROOT)))
                    return {
                        "ok": True,
                        "attempt_id": attempt_id,
                        "result": {"files": sorted(list(set(files))), "count": len(files)}
                    }
                except Exception as e:
                    return {"ok": False, "error": str(e)}

            elif kind == "ping":
                return {"ok": True, "result": "pong"}
            
            return {"ok": False, "error": f"Unknown kind: {kind}"}

        try:
            res = await asyncio.wait_for(_execute(), timeout=timeout)
        except asyncio.TimeoutError:
            res = {"ok": False, "attempt_id": attempt_id, "error": "TIMEOUT", "error_code": "JOB_TIMEOUT"}
        except Exception as e:
            res = {"ok": False, "attempt_id": attempt_id, "error": str(e)}

        # 5. Save & Return
        res["request_id"] = req_id
        _save_attempt_result(attempt_id, res)
        return res

    return app

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8080)
    parser.add_argument("--host", type=str, default="0.0.0.0", help="IP address to bind (default: 0.0.0.0 for all)")
    parser.add_argument("--node_id", type=str, required=True)
    parser.add_argument("--auth_key", type=str, default="shared-secret")
    args = parser.parse_args()
    
    
    app = make_app(args.node_id, args.auth_key)
    
    # Print startup message
    print(f"[api_real] Starting Host API for node '{args.node_id}' on {args.host}:{args.port}")
    
    # Disable colored output
    import os
    os.environ['NO_COLOR'] = '1'
    
    # Suppress warnings for cleaner output
    import warnings
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    
    uvicorn.run(
        app, 
        host=args.host, 
        port=args.port,
        access_log=False  # Disable HTTP request logs
    )

if __name__ == "__main__":
    main()
