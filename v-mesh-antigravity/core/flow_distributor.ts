// core/flow_distributor.ts

interface NodeIntegritiy {
    id: string;
    latency: number;      // ms (Pinging)
    energyCost: number;   // Relativer Strompreis/Verbrauch
    thermalLoad: number;  // Hardware-Stress (0-1)
    stability: number;    // Historische Verlässlichkeit
}

export class FlowDistributor {
    // Die "Gravitations-Konstante" für das System
    private readonly G = 1.0;

    calculateResistance(node: NodeIntegritiy): number {
        // Widerstand R = (Latenz * Energie) / (Integrität * Stabilität)
        // Je höher der Widerstand, desto "schwerer" ist der Knoten.
        const resistance = (node.latency * node.energyCost) /
            ((1 - node.thermalLoad) * node.stability);
        return resistance;
    }

    findBestSynapse(nodes: NodeIntegritiy[]): NodeIntegritiy {
        // Das System sucht den Knoten mit dem geringsten Widerstand
        return nodes.reduce((best, current) =>
            this.calculateResistance(current) < this.calculateResistance(best) ? current : best
        );
    }

    dispatch(vector: any, nodes: NodeIntegritiy[]) {
        const target = this.findBestSynapse(nodes);
        console.log(`Vektor wird zu Synapse ${target.id} geleitet. Widerstand: ${this.calculateResistance(target)}`);
        // Hier folgt der tatsächliche Datenfluss (A/B Routing)
    }
}
