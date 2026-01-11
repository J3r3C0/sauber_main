import json
import time
import os
import re
import sys

# Ensure UTF-8 output on Windows
if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

# V-Mesh Gravity Distributor
# Resonates with the pulse to identify the optimal node.

PROJECT_ROOT = r"C:\projectroot"
LIVE_STREAM_PATH = os.path.join(PROJECT_ROOT, "v_mesh_output", "live_stream.txt")

class GravityDistributor:
    def __init__(self, stream_path):
        self.stream_path = stream_path
        self.current_target = "Host_A"
        print(f"Gravity Distributor initialized. Monitoring: {self.stream_path}")

    def balance_flow(self):
        if not os.path.exists(self.stream_path):
            return
            
        try:
            with open(self.stream_path, 'r', encoding='utf-8') as f:
                content = f.read()
                # Find the last pulse block
                pulses = re.findall(r"--- \[V-MESH PULSE.*?\] ---\n(.*?)\n(?=---|$)", content, re.DOTALL)
                if pulses:
                    last_pulse_json = pulses[-1]
                    data = json.loads(last_pulse_json)
                    best_node = data.get('resonance_target', self.current_target)
                    
                    if best_node != self.current_target:
                        old_target = self.current_target
                        self.current_target = best_node
                        print(f"[GRAVITY_SHIFT] Resonance shift: {old_target} -> {self.current_target}")
                    else:
                        sys.stdout.write('.')
                        sys.stdout.flush()
        except Exception as e:
            print(f"Error during balancing: {e}")

def run():
    distributor = GravityDistributor(LIVE_STREAM_PATH)
    while True:
        distributor.balance_flow()
        time.sleep(5)

if __name__ == "__main__":
    run()
