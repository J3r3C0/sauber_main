import { apiClient } from '../api/client';

interface EndpointHealth {
    endpoint: string;
    status: 'healthy' | 'degraded' | 'down';
    responseTime?: number;
    error?: string;
}

export interface SystemHealth {
    overall: 'healthy' | 'degraded' | 'down';
    endpoints: EndpointHealth[];
    timestamp: string;
}

// Prüfe einen einzelnen Endpoint
async function checkEndpoint(path: string): Promise<EndpointHealth> {
    const start = Date.now();
    try {
        await apiClient.get(path, { timeout: 3000 });
        const responseTime = Date.now() - start;

        return {
            endpoint: path,
            status: responseTime < 1000 ? 'healthy' : 'degraded',
            responseTime,
        };
    } catch (error: any) {
        return {
            endpoint: path,
            status: 'down',
            error: error.message || 'Connection failed',
        };
    }
}

// Prüfe alle wichtigen Endpoints
export async function checkSystemHealth(): Promise<SystemHealth> {
    const endpoints = [
        '/status',      // System Health
        '/missions',    // Missions API
        '/tasks',       // Tasks API
        '/jobs',        // Jobs API
    ];

    const results = await Promise.all(
        endpoints.map(endpoint => checkEndpoint(endpoint))
    );

    // Berechne Overall-Status
    const downCount = results.filter(r => r.status === 'down').length;
    const degradedCount = results.filter(r => r.status === 'degraded').length;

    let overall: SystemHealth['overall'];
    if (downCount > 0) {
        overall = downCount >= results.length / 2 ? 'down' : 'degraded';
    } else if (degradedCount > 0) {
        overall = 'degraded';
    } else {
        overall = 'healthy';
    }

    return {
        overall,
        endpoints: results,
        timestamp: new Date().toISOString(),
    };
}
