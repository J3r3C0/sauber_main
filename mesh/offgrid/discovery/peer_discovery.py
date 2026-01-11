#!/usr/bin/env python3
"""Simple UDP peer discovery for off-grid (local link)

- Broadcasts a small JSON "iamhere" with node_id & endpoint
- Listens for peers; writes/updates discovery/mesh_hosts.json
"""
import socket, json, time, threading
from pathlib import Path

BCAST_ADDR = "<broadcast>"
PORT = 45888
INTERVAL = 3.0
HOSTS_FILE = Path("./discovery/mesh_hosts.json")
from discovery.atomic_hosts import merge_entry

def sender(node_id: str, endpoint: str, stop_flag):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    pkt = json.dumps({"t":"iamhere","node_id":node_id,"endpoint":endpoint}).encode()
    while not stop_flag["stop"]:
        s.sendto(pkt, (BCAST_ADDR, PORT))
        time.sleep(INTERVAL)

def receiver(stop_flag):
    HOSTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not HOSTS_FILE.exists():
        HOSTS_FILE.write_text("{}", encoding="utf-8")
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("", PORT))
    s.settimeout(1.0)
    while not stop_flag["stop"]:
        try:
            data, addr = s.recvfrom(4096)
            obj = json.loads(data.decode())
            if obj.get("t") == "iamhere" and "endpoint" in obj:
                merge_entry(obj["endpoint"], obj.get("node_id","?"), "udp")
        except socket.timeout:
            pass
        except Exception:
            pass

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--node_id", default="node-A")
    ap.add_argument("--endpoint", default="http://127.0.0.1:8081")
    args = ap.parse_args()
    stop = {"stop": False}
    ts = threading.Thread(target=sender, args=(args.node_id, args.endpoint, stop), daemon=True)
    tr = threading.Thread(target=receiver, args=(stop,), daemon=True)
    ts.start(); tr.start()
    print("[discovery] broadcasting + listening (Ctrl+C to stop)")
    try:
        while True: time.sleep(1)
    except KeyboardInterrupt:
        stop["stop"] = True

if __name__ == "__main__":
    main()
