import { apiClient, backendPocClient } from './client';
import type { Job, LoopState } from '../types';

// API Response Types
interface TaskApiResponse {
    id: string;
    mission_id: string;
    name: string;
}

interface JobApiResponse {
    id: string;
    task_id: string;
    status: string;
    payload?: {
        loop_state?: LoopState;
        [key: string]: any;
    };
    result?: any;
}

// Quick Start Response from Backend PoC
interface QuickStartResponse {
    mission: { id: string; title: string };
    task: { id: string; name: string };
    job?: { id: string };
}

// Self-Loop Job Payload
interface SelfLoopPayload {
    job_type: 'sheratan_selfloop';
    goal: string;
    loop_state: LoopState;
    llm?: {
        mode: string;
        model_hint?: string;
        temperature?: number;
        max_tokens?: number;
    };
    input_context?: {
        core_data?: string;
        current_task?: string;
    };
}

// Create initial loop state
const createInitialLoopState = (): LoopState => ({
    iteration: 1,
    history_summary: '',
    open_questions: [],
    constraints: [],
});

export const selfloopApi = {
    /**
     * 🚀 Quick Start: Standard Code Analysis
     * Uses Backend PoC to create a complete self-loop mission with one click
     * This is the recommended way to start a Self-Loop!
     */
    quickStartCodeAnalysis: async (): Promise<QuickStartResponse> => {
        console.log('🚀 Starting Quick Code Analysis via Backend PoC...');
        const response = await backendPocClient.post<QuickStartResponse>('/missions/standard-code-analysis');
        console.log('✅ Quick Start response:', response.data);
        return response.data;
    },

    /**
     * Create a Self-Loop task for a mission
     */
    createTask: async (missionId: string, name: string = 'Self-Loop Task'): Promise<TaskApiResponse> => {
        const response = await apiClient.post<TaskApiResponse>(`/missions/${missionId}/tasks`, {
            name,
            description: 'Autonomous self-loop task for iterative goal achievement',
            kind: 'selfloop',
            params: {},
        });
        return response.data;
    },

    /**
     * Create a Self-Loop job with sheratan_selfloop type
     */
    createSelfLoopJob: async (
        taskId: string,
        goal: string,
        options?: {
            loopState?: LoopState;
            modelHint?: string;
            temperature?: number;
        }
    ): Promise<JobApiResponse> => {
        const payload: SelfLoopPayload = {
            job_type: 'sheratan_selfloop',
            goal,
            loop_state: options?.loopState || createInitialLoopState(),
            llm: {
                mode: 'relay',
                model_hint: options?.modelHint || 'gpt-4o',
                temperature: options?.temperature ?? 0.3,
                max_tokens: 1200,
            },
            input_context: {
                core_data: 'Relevant project context',
                current_task: goal,
            },
        };

        const response = await apiClient.post<JobApiResponse>(`/tasks/${taskId}/jobs`, payload);
        return response.data;
    },

    /**
     * Start a complete Self-Loop: Create task + job + dispatch
     * Convenience method that combines all steps
     */
    startSelfLoop: async (
        missionId: string,
        goal: string,
        options?: {
            modelHint?: string;
            temperature?: number;
        }
    ): Promise<{ task: TaskApiResponse; job: JobApiResponse }> => {
        // 1. Create task for mission
        const task = await selfloopApi.createTask(missionId, `Self-Loop: ${goal.substring(0, 30)}...`);

        // 2. Create self-loop job
        const job = await selfloopApi.createSelfLoopJob(task.id, goal, options);

        // 3. Dispatch the job
        await apiClient.post(`/jobs/${job.id}/dispatch`);

        console.log('🔄 Self-Loop started:', { missionId, taskId: task.id, jobId: job.id });

        return { task, job };
    },

    /**
     * Get all self-loop jobs for a mission
     */
    getSelfLoopJobs: async (missionId: string): Promise<Job[]> => {
        // Get tasks for mission
        const tasksRes = await apiClient.get<TaskApiResponse[]>('/tasks');
        const missionTasks = tasksRes.data.filter(t => t.mission_id === missionId);
        const taskIds = new Set(missionTasks.map(t => t.id));

        // Get jobs and filter for self-loop type
        const jobsRes = await apiClient.get<JobApiResponse[]>('/jobs');
        const selfLoopJobs = jobsRes.data.filter(j =>
            taskIds.has(j.task_id) &&
            j.payload?.loop_state !== undefined
        );

        // Transform to frontend Job type
        return selfLoopJobs.map(j => ({
            id: j.id,
            missionId: j.task_id,
            agent: 'selfloop',
            type: 'selfloop' as const,
            status: mapStatus(j.status),
            startedAt: new Date().toISOString(),
            payload: j.payload,
            result: j.result,
        }));
    },

    /**
     * Get loop state from the latest self-loop job
     */
    getLatestLoopState: async (missionId: string): Promise<LoopState | null> => {
        const jobs = await selfloopApi.getSelfLoopJobs(missionId);
        const doneJobs = jobs.filter(j => j.status === 'done' && j.payload?.loop_state);

        if (doneJobs.length === 0) return null;

        // Return the highest iteration
        const sortedJobs = doneJobs.sort((a, b) =>
            (b.payload?.loop_state?.iteration || 0) - (a.payload?.loop_state?.iteration || 0)
        );

        return sortedJobs[0]?.payload?.loop_state || null;
    },

    /**
     * Continue a self-loop with the next iteration
     */
    continueLoop: async (
        taskId: string,
        goal: string,
        previousLoopState: LoopState,
        historySummary: string
    ): Promise<JobApiResponse> => {
        const nextLoopState: LoopState = {
            iteration: previousLoopState.iteration + 1,
            history_summary: historySummary,
            open_questions: previousLoopState.open_questions,
            constraints: previousLoopState.constraints,
        };

        return selfloopApi.createSelfLoopJob(taskId, goal, { loopState: nextLoopState });
    },
};

// Helper: Map backend status to frontend status
const mapStatus = (status: string): Job['status'] => {
    const lower = status?.toLowerCase() || '';
    if (lower.includes('done') || lower.includes('complete')) return 'done';
    if (lower.includes('fail') || lower.includes('error')) return 'error';
    if (lower.includes('work') || lower.includes('progress')) return 'working';
    return 'queued';
};

export type { SelfLoopPayload, LoopState };
