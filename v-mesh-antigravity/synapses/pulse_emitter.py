import asyncio
import websockets
import json
import time
import sys
import os

# Ensure we can import from .sys
sys.path.append(os.path.join(os.path.dirname(__current_file__), '../.sys'))
from integrity import NodeSensor

async def send_pulse(uri, node_id):
    sensor = NodeSensor(node_id)
    
    async with websockets.connect(uri) as websocket:
        while True:
            # 1. Lokale Integrität messen
            stats = sensor.get_current_integrity()
            
            # 2. Lokalen Widerstand berechnen (einfache Gravitations-Logik)
            # R = (Last + Energie) * (1 / Stabilität)
            resistance = (stats['thermalLoad'] + stats['energyCost']) / stats['stability']
            
            pulse = {
                "id": node_id,
                "resistance": round(resistance, 4),
                "timestamp": time.time(),
                "thermalLoad": stats['thermalLoad'],
                "energyCost": stats['energyCost'],
                "stability": stats['stability']
            }
            
            # 3. Den Puls in das V-Mesh "ausatmen"
            await websocket.send(json.dumps(pulse))
            
            # Intervall der Neukalibrierung (Konstanter Flow)
            await asyncio.sleep(1) 

if __name__ == "__main__":
    node_id = os.getenv("NODE_ID", "HOST_A")
    hub_uri = os.getenv("HUB_URI", "ws://localhost:8080")
    print(f"Starting Pulse Emitter for {node_id} connecting to {hub_uri}...")
    asyncio.get_event_loop().run_until_complete(send_pulse(hub_uri, node_id))
