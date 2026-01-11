import { apiClient } from './client';

// Task API Types
export interface Task {
    id: string;
    missionId: string;
    name: string;
    kind?: string;
    status?: 'pending' | 'running' | 'completed' | 'failed';
    createdAt: string;
    updatedAt?: string;
}

interface TaskApiResponse {
    id: string;
    mission_id: string;
    name: string;
    kind?: string;
    status?: string;
    created_at: string;
    updated_at?: string;
}

// Transform API → Frontend
const transformTask = (apiTask: TaskApiResponse): Task => ({
    id: apiTask.id,
    missionId: apiTask.mission_id,
    name: apiTask.name || 'Unnamed Task',
    kind: apiTask.kind,
    status: (apiTask.status as Task['status']) || 'pending',
    createdAt: apiTask.created_at,
    updatedAt: apiTask.updated_at,
});

export const tasksApi = {
    // GET alle Tasks
    getAll: async (): Promise<Task[]> => {
        const response = await apiClient.get<TaskApiResponse[]>('/tasks');
        return response.data.map(transformTask);
    },

    // GET Tasks für eine Mission
    getByMissionId: async (missionId: string): Promise<Task[]> => {
        const response = await apiClient.get<TaskApiResponse[]>('/tasks');
        return response.data
            .filter(t => t.mission_id === missionId)
            .map(transformTask);
    },

    // GET einzelner Task
    getById: async (id: string): Promise<Task> => {
        const response = await apiClient.get<TaskApiResponse>(`/tasks/${id}`);
        return transformTask(response.data);
    },

    // POST neuer Task
    create: async (data: { mission_id: string; name: string; kind?: string }): Promise<Task> => {
        const response = await apiClient.post<TaskApiResponse>('/tasks', data);
        return transformTask(response.data);
    },
};
