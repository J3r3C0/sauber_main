import time
import json
import os
import subprocess
import re
import sys

# Gravity Balance Core v3
# Transition: Simulation -> Real-World Resonance
# Part of the V-Mesh Genesis Phase

PROJECT_ROOT = r"C:\projectroot"
LIVE_STREAM_PATH = os.path.join(PROJECT_ROOT, "v_mesh_output", "live_stream.txt")
NODE_B_IP = "192.168.1.127" # The Tower

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

def get_real_latency(ip):
    """
    Measures real network latency via ICMP ping.
    Returns latency in ms.
    """
    try:
        # Ping with 1 packet, 1s timeout
        output = subprocess.check_output(["ping", "-n", "1", "-w", "1000", ip], universal_newlines=True)
        match = re.search(r"Zeit[=<](\d+)ms", output)
        if match:
            return int(match.group(1))
    except Exception:
        pass
    return 999 # High resistance if unreachable

def calculate_resonance(node_a, node_b):
    """
    Sheratan Core Logic: Stability through dynamic weight distribution.
    Lower resistance (load * latency) indicates a more stable target.
    """
    resistance_a = node_a['load'] * node_a['latency']
    resistance_b = node_b['load'] * node_b['latency']
    
    return 'Host_A' if resistance_a <= resistance_b else 'Host_B'

def run():
    print("Gravity Balance Core v3 starting (Live Mode)...")
    print(f"Targeting Node B: {NODE_B_IP}")
    
    while True:
        # Host A (Local Laptop) is considered high performance/low latency (baseline 1ms)
        node_a = {'load': 0.42, 'latency': 1}
        
        # Host B (Tower) latency is now measured in real-time
        latency_b = get_real_latency(NODE_B_IP)
        node_b = {'load': 0.35, 'latency': latency_b}
        
        target = calculate_resonance(node_a, node_b)
        
        status = {
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
            'resonance_target': target,
            'entropy_level': 0.042,
            'nodes': {
                'Host_A': node_a,
                'Host_B': node_b
            }
        }
        
        log_entry = f"\n\n--- [V-MESH PULSE {status['timestamp']}] ---\n{json.dumps(status, indent=2)}\n"
        
        try:
            with open(LIVE_STREAM_PATH, 'a', encoding='utf-8') as f:
                f.write(log_entry)
            print(f"[{status['timestamp']}] Pulse: {target} (Node B Latenz: {latency_b}ms)")
        except Exception as e:
            print(f"Friction detected: {e}")
            
        time.sleep(10)

if __name__ == "__main__":
    run()
