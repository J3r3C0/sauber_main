import { apiClient } from './client';
import { Job } from '../types';

// ECHTE API Response Struktur
interface JobApiResponse {
    id: string;
    task_id?: string;
    payload?: any;
    status?: string;
    result?: any;
    created_at?: string;
    updated_at?: string;
}

// Map Backend-Status zu Frontend-Status
const mapJobStatus = (status?: string): Job['status'] => {
    if (!status) return 'queued';
    const lowerStatus = status.toLowerCase();
    if (lowerStatus.includes('done') || lowerStatus.includes('complete')) return 'done';
    if (lowerStatus.includes('fail') || lowerStatus.includes('error')) return 'error';
    if (lowerStatus.includes('work') || lowerStatus.includes('progress')) return 'working';
    return 'queued';
};

// Robuste Transformation mit Fehlerbehandlung
const transformJob = (apiJob: JobApiResponse): Job | null => {
    try {
        if (!apiJob || !apiJob.id) {
            console.warn('Invalid job data:', apiJob);
            return null;
        }

        return {
            id: apiJob.id,
            missionId: apiJob.task_id || 'unknown',
            agent: apiJob.result?.worker_id || 'agent',
            type: (apiJob.payload?.task?.kind || apiJob.status === 'pending' ? 'analysis' : 'task') as any, // Fallback logic
            status: mapJobStatus(apiJob.status),
            startedAt: apiJob.created_at || new Date().toISOString(),
            finishedAt: apiJob.updated_at,
            duration: undefined,
            payload: apiJob.payload || {},
            result: apiJob.result || null,
        };
    } catch (error) {
        console.error('Error transforming job:', apiJob, error);
        return null;
    }
};

export const jobsApi = {
    getAll: async (): Promise<Job[]> => {
        try {
            const response = await apiClient.get<JobApiResponse[]>('/jobs');
            console.log('✅ Jobs API Response:', {
                status: response.status,
                count: response.data?.length || 0,
                sample: response.data?.[0]
            });

            if (!Array.isArray(response.data)) {
                console.error('❌ Jobs response is not an array:', response.data);
                return [];
            }

            const jobs = response.data
                .map(transformJob)
                .filter((job): job is Job => job !== null);

            console.log(`✅ Transformed ${jobs.length} jobs successfully`);
            return jobs;
        } catch (error) {
            console.error('❌ Jobs API Error:', error);
            return [];
        }
    },

    getById: async (id: string): Promise<Job> => {
        const response = await apiClient.get<JobApiResponse>(`/jobs/${id}`);
        const job = transformJob(response.data);
        if (!job) throw new Error(`Failed to transform job ${id}`);
        return job;
    },

    create: async (data: Partial<Job>): Promise<Job> => {
        const response = await apiClient.post<JobApiResponse>('/jobs', data);
        const job = transformJob(response.data);
        if (!job) throw new Error('Failed to transform created job');
        return job;
    },

    dispatch: async (jobId: string): Promise<void> => {
        await apiClient.post(`/jobs/${jobId}/dispatch`);
    },

    sync: async (jobId: string): Promise<Job> => {
        const response = await apiClient.post<JobApiResponse>(`/jobs/${jobId}/sync`);
        const job = transformJob(response.data);
        if (!job) throw new Error(`Failed to transform synced job ${jobId}`);
        return job;
    },

    delete: async (jobId: string): Promise<void> => {
        await apiClient.delete(`/jobs/${jobId}`);
    },
};
