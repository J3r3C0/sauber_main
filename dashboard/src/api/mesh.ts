import { coreApiClient } from './client';
import { MeshNode } from '../types';

export interface WorkerCapability {
    kind: string;
    cost: number;
}

export interface WorkerInfo {
    worker_id: string;
    capabilities: WorkerCapability[];
    status: string;
    last_seen: number;
    endpoint?: string;
}

export interface LedgerInfo {
    user_id: string;
    balance: number;
    transfers: any[];
}

// Transformation: Backend Worker → Frontend MeshNode
const transformWorker = (w: WorkerInfo): MeshNode => ({
    id: w.worker_id,
    name: w.worker_id,
    role: "worker",
    status: w.status === "online" ? "online" : "offline",
    ip: w.endpoint || "local",
    port: 0, // Not explicitly in WorkerInfo yet
    latency: Math.floor(Math.random() * 20) + 2, // Mock latency for now
    score: 95,
    lastSeen: new Date(w.last_seen * 1000).toISOString(),
    endpoints: w.capabilities.map(c => `${c.kind} (${c.cost})`),
});

export const meshApi = {
    getWorkers: async (): Promise<MeshNode[]> => {
        try {
            const response = await coreApiClient.get<WorkerInfo[]>('/mesh/workers');
            return response.data.map(transformWorker);
        } catch (error) {
            console.error('Failed to fetch mesh workers:', error);
            return [];
        }
    },

    getLedger: async (userId: string = "alice"): Promise<LedgerInfo> => {
        try {
            const response = await coreApiClient.get<LedgerInfo>(`/mesh/ledger/${userId}`);
            return response.data;
        } catch (error) {
            console.error(`Failed to fetch ledger for ${userId}:`, error);
            return { user_id: userId, balance: 0, transfers: [] };
        }
    }
};
