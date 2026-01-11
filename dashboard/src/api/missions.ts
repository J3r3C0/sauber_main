import { apiClient } from './client';
import { Mission } from '../types';

// API Response Typen
interface MissionApiResponse {
    id: string;
    title?: string;  // Core API uses 'title'
    name?: string;   // Legacy fallback
    description?: string;
    status: string;
    created_at: string;
    updated_at: string;
    tags?: string[];
    metadata?: { [key: string]: any };
}

interface TaskApiResponse {
    id: string;
    mission_id: string;
}

interface JobApiResponse {
    id: string;
    task_id: string;
    status?: string;
}

// Transformation: API → Frontend
const transformMission = (
    apiMission: MissionApiResponse,
    jobStats?: { total: number; completed: number }
): Mission => ({
    id: apiMission.id,
    name: apiMission.title || apiMission.name || `Mission ${apiMission.id.substring(0, 8)}`,
    status: (apiMission.status as Mission['status']) || 'planned',
    createdAt: apiMission.created_at,
    lastUpdate: apiMission.updated_at,
    priority: 'normal',
    progress: jobStats && jobStats.total > 0
        ? Math.round((jobStats.completed / jobStats.total) * 100)
        : 0,
    jobsTotal: jobStats?.total || 0,
    jobsCompleted: jobStats?.completed || 0,
    tags: apiMission.tags,
    metadata: apiMission.metadata,
});

export const missionsApi = {
    // GET alle Missions MIT Job-Stats (STABILE VERSION - Tasks API)
    getAll: async (): Promise<Mission[]> => {
        try {
            // Parallel laden: Missions, Tasks, Jobs
            const [missionsRes, tasksRes, jobsRes] = await Promise.all([
                apiClient.get<MissionApiResponse[]>('/missions'),
                apiClient.get<TaskApiResponse[]>('/tasks'),
                apiClient.get<JobApiResponse[]>('/jobs'),
            ]);

            const missions = missionsRes.data;
            const tasks = tasksRes.data;
            const jobs = jobsRes.data;

            // Für jede Mission: Berechne Job-Stats
            return missions.map(mission => {
                const missionTasks = tasks.filter(t => t.mission_id === mission.id);
                const taskIds = new Set(missionTasks.map(t => t.id));
                const missionJobs = jobs.filter(j => taskIds.has(j.task_id));

                const total = missionJobs.length;
                const completed = missionJobs.filter(j =>
                    j.status === 'done' || j.status === 'completed'
                ).length;

                return transformMission(mission, { total, completed });
            });
        } catch (error) {
            console.error('Failed to load missions with stats:', error);
            const response = await apiClient.get<MissionApiResponse[]>('/missions');
            return response.data.map(m => transformMission(m));
        }
    },

    getById: async (id: string): Promise<Mission> => {
        const response = await apiClient.get<MissionApiResponse>(`/missions/${id}`);
        return transformMission(response.data);
    },

    create: async (data: { title: string; description: string; tags?: string[] }): Promise<Mission> => {
        const response = await apiClient.post<MissionApiResponse>('/missions', {
            title: data.title,
            description: data.description,
            tags: data.tags || [],
            metadata: {},
        });
        return transformMission(response.data);
    },

    delete: async (id: string): Promise<void> => {
        await apiClient.delete(`/missions/${id}`);
    },
};
