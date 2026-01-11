import { apiClient } from './client';

// Fetch job queue count
export const getJobsCount = async (): Promise<number> => {
    const response = await apiClient.get<any[]>('/jobs');
    return response.data.length;
};

// Fetch active jobs (not done, not failed)
export const getActiveJobsCount = async (): Promise<number> => {
    const response = await apiClient.get<any[]>('/jobs');
    return response.data.filter(j =>
        j.status !== 'done' && j.status !== 'failed'
    ).length;
};

// Check Core API status  
export const getCoreStatus = async (): Promise<{ status: string; missions: number }> => {
    const response = await apiClient.get('/status');
    return response.data;
};

// System status for header bar
export interface LiveSystemStatus {
    selfloopState: 'running' | 'degraded' | 'stopped';
    activeModel: string;
    meshNodesOnline: number;
    meshNodesTotal: number;
    jobsInQueue: number;
    unreadAlerts: number;
}

export const getLiveSystemStatus = async (): Promise<LiveSystemStatus> => {
    try {
        const [statusRes, jobsRes, meshRes] = await Promise.all([
            apiClient.get('/status'),
            apiClient.get<any[]>('/jobs'),
            apiClient.get<any[]>('/mesh/workers'),
        ]);

        const jobs = jobsRes.data || [];
        const workers = meshRes.data || [];
        const activeJobs = jobs.filter(j => j.status !== 'done' && j.status !== 'failed');
        const runningJobs = jobs.filter(j => j.status === 'running' || j.status === 'working');

        // Determine selfloop state based on running jobs
        let selfloopState: LiveSystemStatus['selfloopState'] = 'stopped';
        if (runningJobs.length > 0) {
            selfloopState = 'running';
        } else if (activeJobs.length > 0) {
            selfloopState = 'degraded';
        }

        return {
            selfloopState,
            activeModel: statusRes.data.model || 'Llama 3.1 8B (Mesh)',
            meshNodesOnline: workers.filter(w => w.status === 'online').length,
            meshNodesTotal: workers.length,
            jobsInQueue: activeJobs.length,
            unreadAlerts: jobs.filter(j => j.status === 'failed').length,
        };
    } catch (error) {
        console.error('Failed to fetch live system status:', error);
        return {
            selfloopState: 'stopped',
            activeModel: 'unknown',
            meshNodesOnline: 0,
            meshNodesTotal: 0,
            jobsInQueue: 0,
            unreadAlerts: 0,
        };
    }
};

export const getSystemMetrics = async () => {
    try {
        const response = await apiClient.get('/system/metrics');
        return response.data;
    } catch (error) {
        console.error('Failed to fetch system metrics:', error);
        return { cpu: 0, memory: 0, queueLength: 0, errorRate: 0 };
    }
};

export const getSystemHealth = async () => {
    try {
        const response = await apiClient.get('/system/health');
        return response.data;
    } catch (error) {
        console.error('Failed to fetch system health:', error);
        return [];
    }
};
