import { apiClient } from '../api/client';
import type { ServiceNode } from '../types';

export interface SystemHealth {
    overall: 'healthy' | 'degraded' | 'down';
    services: ServiceNode[];
    timestamp: string;
}

/**
 * Fetches comprehensive system health from the Core API
 * This returns the status of all backend services (Relay, Broker, etc.)
 */
export async function checkSystemHealth(): Promise<ServiceNode[]> {
    try {
        const response = await apiClient.get<ServiceNode[]>('/system/health');
        return response.data;
    } catch (error: any) {
        console.error('Failed to fetch system health:', error);
        // Return a mock "down" state for the Core API at least
        return [
            {
                id: 'core-api',
                name: 'Core API',
                status: 'down',
                type: 'core',
                port: 8001,
                dependencies: [],
                uptime: 'N/A'
            }
        ];
    }
}
