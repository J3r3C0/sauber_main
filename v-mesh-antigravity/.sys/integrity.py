# synapses/integrity.py
import psutil
import time

class NodeSensor:
    def __init__(self, node_id):
        self.node_id = node_id

    def get_current_integrity(self):
        # Erfasst reale Hardware-Metriken
        cpu_usage = psutil.cpu_percent() / 100.0
        battery = psutil.sensors_battery()
        
        # Energie-Widerstand steigt, wenn der Akku leer wird
        energy_resistance = 1.0
        if battery and not battery.power_plugged:
            energy_resistance = 1.0 + (1.0 - battery.percent / 100.0)

        return {
            "id": self.node_id,
            "thermalLoad": cpu_usage,
            "energyCost": energy_resistance,
            "stability": 0.95 # Ein statischer Wert, der über Zeit gelernt wird
        }

if __name__ == "__main__":
    # Loop zur permanenten Neukalibrierung
    sensor = NodeSensor("Local-Synapse-A")
    while True:
        print(f"Reporting Integrity: {sensor.get_current_integrity()}")
        time.sleep(5) # Der konstante Puls des Systems
