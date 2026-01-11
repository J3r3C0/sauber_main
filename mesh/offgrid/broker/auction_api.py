#!/usr/bin/env python3
"""
Sheratan Offgrid Broker - Auction API
Handles job auctions and dispatches to best bidder.
"""

import sys
import os
import json
import time
import hmac
import hashlib
import argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime, timedelta

# Add parent directories to path for imports
_broker_dir = Path(__file__).parent
_offgrid_dir = _broker_dir.parent
_mesh_dir = _offgrid_dir.parent
_project_root = _mesh_dir.parent

for p in [str(_offgrid_dir), str(_mesh_dir), str(_project_root)]:
    if p not in sys.path:
        sys.path.insert(0, p)

# Import existing broker logic and consensus
try:
    from consensus import quorum
    from broker_stub import micro_auction, dispatch, _load_rep, _save_rep
except ImportError:
    # Fallback for local development
    sys.path.append(str(_broker_dir))
    from consensus import quorum
    from broker_stub import micro_auction, dispatch, _load_rep, _save_rep

# Configuration  
RESULTS_CACHE = {}  # Store results for polling

class HostMonitor:
    """Monitoring thread that periodically pings discovered hosts."""
    def __init__(self, interval: int = 30):
        self.interval = interval
        self.hosts_file = None
        self._find_hosts_file()

    def _find_hosts_file(self):
        broker_dir = Path(__file__).parent
        cwd = Path.cwd()
        possible_paths = [
            cwd / "discovery" / "mesh_hosts.json",
            broker_dir.parent / "discovery" / "mesh_hosts.json"
        ]
        for path in possible_paths:
            if path.exists():
                self.hosts_file = path
                break

    def _ping_host(self, host: str) -> bool:
        """Ping a host's /status endpoint."""
        import requests
        try:
            resp = requests.get(f"{host}/status", timeout=2)
            return resp.status_code == 200
        except Exception:
            return False

    def run(self):
        """Main monitoring loop."""
        import threading
        def _loop():
            while True:
                if self.hosts_file and self.hosts_file.exists():
                    try:
                        data = json.loads(self.hosts_file.read_text(encoding="utf-8"))
                        changed = False
                        for host in data:
                            is_active = self._ping_host(host)
                            if data[host].get("active") != is_active:
                                data[host]["active"] = is_active
                                data[host]["last_seen"] = datetime.utcnow().isoformat() + "Z" if is_active else data[host].get("last_seen")
                                changed = True
                        
                        if changed:
                            self.hosts_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
                            print(f"[monitor] Updated host health states.")
                    except Exception as e:
                        print(f"[monitor] Error: {e}")
                
                time.sleep(self.interval)

        t = threading.Thread(target=_loop, daemon=True)
        t.start()
        print(f"[monitor] Background host health monitoring started.")


class NoHostsAvailable(Exception):
    """No hosts available for auction."""
    pass


class AuctionHandler(BaseHTTPRequestHandler):
    """HTTP handler for auction requests."""
    
    auth_key = "shared-secret"  # Class variable
    
    def _send_json(self, code: int, data: dict):
        """Send JSON response."""
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_GET(self):
        """Handle GET requests."""
        u = urlparse(self.path)
        
        if u.path == "/status":
            # Health check
            self._send_json(200, {
                "status": "ok",
                "service": "offgrid-broker-auction",
                "version": "0.16.4"
            })
        
        elif u.path.startswith("/results/"):
            # Get cached result
            job_id = u.path.split("/")[-1]
            if job_id in RESULTS_CACHE:
                self._send_json(200, RESULTS_CACHE[job_id])
            else:
                self._send_json(404, {"error": "result not found"})
        
        elif u.path == "/quorum/list":
            # GET /quorum/list?kind=...
            from urllib.parse import parse_qs
            qs = parse_qs(u.query or "")
            kind = qs.get("kind", [None])[0]
            self._send_json(200, quorum.list_records(kind))
            
        elif u.path.startswith("/quorum/status/"):
            # GET /quorum/status/{kind}/{id}
            parts = u.path.split("/")
            if len(parts) >= 5:
                kind = parts[3]
                qid = parts[4]
                rec = quorum.get_record(qid, kind)
                if rec:
                    self._send_json(200, rec)
                else:
                    self._send_json(404, {"error": "quorum record not found"})
            else:
                self._send_json(400, {"error": "invalid path format, expected /quorum/status/{kind}/{id}"})
        
        elif u.path == "/quorum/policy":
            # GET /quorum/policy?kind=...
            from urllib.parse import parse_qs
            qs = parse_qs(u.query or "")
            kind = qs.get("kind", [None])[0]
            self._send_json(200, quorum.get_policy(kind))
        
        else:
            self._send_json(404, {"error": "not found"})
    
    def do_POST(self):
        """Handle POST requests."""
        u = urlparse(self.path)
        
        if u.path == "/auction":
            # Read request body
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            
            try:
                payload = json.loads(body.decode())
            except json.JSONDecodeError:
                self._send_json(400, {"error": "invalid json"})
                return
            
            # Verify signature
            if not self._verify_signature(payload):
                self._send_json(401, {"error": "invalid signature"})
                return
            
            # Check timestamp (prevent replay attacks)
            timestamp = payload.get("timestamp", 0)
            if abs(time.time() - timestamp) > 300:  # 5 minute window
                self._send_json(401, {"error": "timestamp too old"})
                return
            
            # Run auction
            req_id = payload.get("req_id", "unknown")
            try:
                result = self._handle_auction(payload)
                result["req_id"] = req_id # Tag response
                self._send_json(200, result)
            except NoHostsAvailable:
                print(f"[auction_api] [req={req_id}] No hosts available")
                self._send_json(503, {"error": "no hosts available", "req_id": req_id})
            except Exception as e:
                import traceback
                print(f"[auction_api] [req={req_id}] ERROR: {e}")
                print(f"[auction_api] [req={req_id}] Payload keys: {list(payload.keys())}")
                print(f"[auction_api] [req={req_id}] Full traceback:")
                traceback.print_exc()
                self._send_json(500, {"error": str(e), "req_id": req_id})
        
        elif u.path in ["/quorum/create", "/quorum/ack"]:
            # Read request body
            length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(length)
            
            try:
                payload = json.loads(body.decode())
            except json.JSONDecodeError:
                self._send_json(400, {"error": "invalid json"})
                return
            
            # Verify signature
            if not self._verify_signature(payload):
                self._send_json(401, {"error": "invalid signature"})
                return
                
            # Check timestamp
            timestamp = payload.get("timestamp", 0)
            if abs(time.time() - timestamp) > 300:
                self._send_json(401, {"error": "timestamp too old"})
                return
                
            if u.path == "/quorum/create":
                res = quorum.create_or_get(payload.get("id"), payload.get("kind"), payload.get("required", 1.0), payload.get("meta"))
                self._send_json(200, res)
            elif u.path == "/quorum/ack":
                res = quorum.add_ack(payload.get("id"), payload.get("kind"), payload.get("node_id"))
                self._send_json(200, res)
        
        else:
            self._send_json(404, {"error": "not found"})
    
    def _verify_signature(self, payload: dict) -> bool:
        """Verify HMAC signature."""
        if "signature" not in payload:
            return False
        
        received_sig = payload.pop("signature")
        
        # Recreate signature
        payload_str = json.dumps(payload, sort_keys=True)
        expected_sig = hmac.new(
            self.auth_key.encode(),
            payload_str.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Put signature back
        payload["signature"] = received_sig
        
        return hmac.compare_digest(received_sig, expected_sig)
    
    def _handle_auction(self, core_job: dict) -> dict:
        """
        Run auction for Core job.
        
        Args:
            core_job: Job spec from Core (already mapped to Offgrid schema)
        
        Returns:
            Result dictionary with host, quote, result, receipt
        """
        
        # Load hosts from discovery
        hosts = self._get_hosts()
        if not hosts:
            raise NoHostsAvailable()
        
        # Load reputation
        rep = _load_rep()
        
        # Extract job spec (schema already converted by Core)
        offgrid_job = {
            "job_id": core_job.get("job_id"),
            "type": core_job.get("type", "compute"),
            "size": core_job.get("size", 0.1),
            "latency_ms": core_job.get("latency_ms", 5000),
            "constraints": core_job.get("constraints", {}),
            "job": core_job.get("job")  # Forward versioned JobSpec v1
        }
        
        print(f"[auction_api] Running auction for job {offgrid_job['job_id']}")
        
        # Apply constraints
        hosts = self._filter_hosts_by_constraints(hosts, offgrid_job["constraints"])
        
        # Run micro-auction
        candidates = micro_auction(hosts, offgrid_job, rep)
        
        if not candidates:
            raise NoHostsAvailable()
        
        # Try candidates in order (best quote first)
        for _, host, quote in candidates:
            print(f"[auction_api] Trying host {host} (quote={quote})")
            
            ok, result = dispatch(host, offgrid_job, t_activate_s=30)
            
            if ok:
                # Success - update reputation
                rep.setdefault(host, {"misses": 0, "hits": 0})
                rep[host]["hits"] += 1
                _save_rep(rep)
                
                # Cache result
                RESULTS_CACHE[offgrid_job["job_id"]] = {
                    "status": "completed",
                    "host": host,
                    "quote": quote,
                    "ok": True,
                    "output": result.get("output", ""),
                    "receipt": result.get("receipt", {})
                }
                
                return RESULTS_CACHE[offgrid_job["job_id"]]
            else:
                # Failure - penalize reputation
                rep.setdefault(host, {"misses": 0, "hits": 0})
                rep[host]["misses"] += 1
                _save_rep(rep)
                print(f"[auction_api] Host {host} failed, trying next...")
        
        # All candidates failed
        raise NoHostsAvailable()
    
    def _get_hosts(self) -> list:
        """Load hosts from discovery or use localhost fallback."""
        # Try multiple paths for discovery file
        broker_dir = Path(__file__).parent
        cwd = Path.cwd()
        
        # Try paths in order: CWD/discovery, script_parent/discovery
        possible_paths = [
            cwd / "discovery" / "mesh_hosts.json",
            broker_dir.parent / "discovery" / "mesh_hosts.json"
        ]
        
        discovery_file = None
        for path in possible_paths:
            if path.exists():
                discovery_file = path
                break
        
        if discovery_file:
            print(f"[auction_api] Looking for discovery at: {discovery_file}")
            try:
                hosts_map = json.loads(discovery_file.read_text(encoding="utf-8"))
                hosts = list(hosts_map.keys())
                print(f"[auction_api] [OK] Found {len(hosts)} hosts from discovery: {hosts}")
                return hosts
            except Exception as e:
                print(f"[auction_api] [WARN] Failed to load discovery: {e}")
        else:
            print(f"[auction_api] Discovery file not found in any expected location")
        
        # Fallback to localhost
        hosts = ["http://127.0.0.1:8081", "http://127.0.0.1:8082"]
        print(f"[auction_api] Using fallback hosts: {hosts}")
        return hosts
    
    def _filter_hosts_by_constraints(self, hosts: list, constraints: dict) -> list:
        """Filter hosts based on job constraints."""
        
        # For now, simple filtering
        # TODO: Query host /mesh endpoint for health metrics
        
        min_mesh_health = constraints.get("min_mesh_health", False)
        if min_mesh_health:
            print(f"[auction_api] Filtering hosts by min_mesh_health={min_mesh_health}")
            # Filter to hosts with mesh_ok=true
            # (would require querying each host's /mesh endpoint)
            pass
        
        return hosts

    def _query_mesh(self, host: str) -> dict:
        """Query host's /mesh endpoint."""
        try:
            response = requests.get(f"{host}/mesh")
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"[auction_api] [WARNING] Failed to query mesh for {host}: {e}")
            return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9000)
    ap.add_argument("--auth_key", type=str, default="shared-secret")
    args = ap.parse_args()
    
    # Set class variable
    AuctionHandler.auth_key = args.auth_key
    
    print(f"[auction_api] Starting Offgrid Auction API on port {args.port}")
    print(f"[auction_api] Auth key: {args.auth_key[:8]}...")
    
    # Start background monitor
    monitor = HostMonitor(interval=15)
    monitor.run()
    
    server = HTTPServer(("0.0.0.0", args.port), AuctionHandler)
    server.serve_forever()


if __name__ == "__main__":
    main()
