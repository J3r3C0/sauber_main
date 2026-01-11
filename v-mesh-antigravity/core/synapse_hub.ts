import { WebSocketServer, WebSocket } from 'ws';

// Der Hub hält den aktuellen Zustand aller verbundenen "Gehirnzellen" (Knoten)
const wss = new WebSocketServer({ port: 8080 });
let synapseNetwork: Map<string, any> = new Map();

wss.on('connection', (ws: WebSocket) => {
    ws.on('message', (data: string) => {
        try {
            const pulse = JSON.parse(data);

            // Jede Synapse sendet ihren "Puls" (Integrität, Last, Preis)
            synapseNetwork.set(pulse.id, {
                ...pulse,
                lastSeen: Date.now(),
                socket: ws
            });

            console.log(`Synapse ${pulse.id} ist synchron. Widerstand aktuell: ${pulse.resistance}`);
        } catch (e) {
            console.error('Failed to parse pulse data:', e);
        }
    });

    ws.on('close', () => {
        // Handle disconnection if needed
    });
});

console.log('V-Mesh Synapse Hub running on port 8080');

// Funktion, um den "leichtesten" Weg für einen Vektor zu finden
export const getOptimalRoute = () => {
    return Array.from(synapseNetwork.values()).sort((a, b) => a.resistance - b.resistance)[0];
};
