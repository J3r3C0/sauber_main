// core/reassembly_proxy.ts

interface Shard {
    id: string;
    index: number;
    total: number;
    data: any;
}

export class ReassemblyProxy {
    private buffer: Map<string, Shard[]> = new Map();

    receiveFragment(vectorId: string, fragment: Shard) {
        if (!this.buffer.has(vectorId)) {
            this.buffer.set(vectorId, []);
        }

        const currentShards = this.buffer.get(vectorId)!;
        currentShards.push(fragment);

        // Prüfe, ob die kritische Masse für die Erkenntnis erreicht ist
        if (currentShards.length === fragment.total) {
            return this.crystallize(vectorId);
        }
        return null; // Warte auf restliche Fragmente
    }

    private crystallize(vectorId: string) {
        const shards = this.buffer.get(vectorId)!.sort((a, b) => a.index - b.index);
        console.log(`Vektor ${vectorId} erfolgreich re-materialisiert.`);
        const result = shards.map(s => s.data).join('');
        this.buffer.delete(vectorId); // Clean up
        return result;
    }
}
