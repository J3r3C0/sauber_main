/**
 * .sys/selection.ts
 * Das Immunsystem des V-Mesh.
 */

interface Shard {
    id: string;
    entropy_cost: number;
}

const SYSTEM_THRESHOLD = 0.8;

export function validateFlow(fragment: Shard): boolean {
    // 1. Hat das Fragment eine reine Absicht? (Signatur-Prüfung - Placeholder)
    // 2. Erzeugt die Verarbeitung dieses Fragments unverhältnismäßige Hitze?
    if (fragment.entropy_cost > SYSTEM_THRESHOLD) {
        console.warn(`Fragment ${fragment.id} abgewiesen: Zu hohe Entropie (Reibung: ${fragment.entropy_cost}).`);
        return false; // Fragment stirbt ab
    }
    return true; // Fragment darf fließen
}
