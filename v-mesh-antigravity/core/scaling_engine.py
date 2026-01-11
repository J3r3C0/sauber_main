# core/scaling_engine.py
import math

class ScalingEngine:
    def __init__(self, cluster_integrity):
        self.nodes = cluster_integrity # Liste der aktuellen Knoten-Widerstände

    def shard_vector(self, complex_payload):
        """
        Zerlegt eine schwere Last in Fragmente (Atome).
        Jedes Atom erhält eine Affinität zu einem bestimmten Knoten-Typ.
        """
        payload_size = len(complex_payload)
        if not self.nodes:
            return [{"target_node": "local", "data_fragment": complex_payload, "priority": "stable"}]

        total_resistance = sum(node['resistance'] for node in self.nodes)
        
        shards = []
        for node in self.nodes:
            # Berechne den Anteil der Last, den dieser Knoten tragen kann
            # Antigravity-Logik: Je niedriger der Widerstand, desto mehr Last zieht er an.
            # Using current sum of inverse resistances (capacities)
            total_capacity = sum(1 / n['resistance'] for n in self.nodes if n['resistance'] > 0)
            if total_capacity == 0:
                 capacity_ratio = 1 / len(self.nodes)
            else:
                 capacity_ratio = (1 / node['resistance']) / total_capacity
            
            shard_size = math.floor(payload_size * capacity_ratio)
            
            shards.append({
                "target_node": node['id'],
                "data_fragment": complex_payload[:shard_size],
                "priority": "stable" if node.get('stability', 0) > 0.9 else "redundant"
            })
            complex_payload = complex_payload[shard_size:]
            
        return shards

if __name__ == "__main__":
    # Beispiel: Eine "schwere" Erkenntnis wird zerlegt
    engine = ScalingEngine([{"id": "A", "resistance": 0.5, "stability": 0.95}, {"id": "B", "resistance": 1.5, "stability": 0.8}])
    atoms = engine.shard_vector("KOMPLEXE_LOGIK_DES_SEINS_VEKTOR_001")
    for a in atoms:
        print(f"Shard for {a['target_node']}: {a['data_fragment']} ({a['priority']})")
