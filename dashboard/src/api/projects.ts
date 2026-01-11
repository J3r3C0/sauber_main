import { coreApiClient } from './client';
import type { Project, FileNode } from '../types';

export const projectsApi = {
    getProjects: async (): Promise<Project[]> => {
        try {
            const response = await coreApiClient.get<any[]>('/projects');
            return response.data.map(p => ({
                id: p.id,
                name: p.name,
                path: p.path,
                status: p.status as "active" | "inactive",
                lastAccess: p.lastAccess,
                fileCount: p.fileCount,
            }));
        } catch (error) {
            console.error('Failed to fetch projects:', error);
            return [];
        }
    },

    getProjectFiles: async (projectId: string): Promise<FileNode[]> => {
        try {
            const response = await coreApiClient.get<FileNode[]>(`/projects/${projectId}/files`);
            return response.data;
        } catch (error) {
            console.error(`Failed to fetch files for project ${projectId}:`, error);
            return [];
        }
    }
};
