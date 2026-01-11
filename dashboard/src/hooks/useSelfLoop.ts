import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { selfloopApi } from '../api/selfloop';

/**
 * Hook for starting a new self-loop
 */
export function useStartSelfLoop() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async ({
            missionId,
            goal,
            options
        }: {
            missionId: string;
            goal: string;
            options?: { modelHint?: string; temperature?: number }
        }) => {
            return selfloopApi.startSelfLoop(missionId, goal, options);
        },
        onSuccess: () => {
            // Invalidate relevant queries
            queryClient.invalidateQueries({ queryKey: ['jobs'] });
            queryClient.invalidateQueries({ queryKey: ['tasks'] });
            queryClient.invalidateQueries({ queryKey: ['missions'] });
        },
    });
}

/**
 * Hook for getting self-loop jobs for a mission
 */
export function useSelfLoopJobs(missionId: string | undefined) {
    return useQuery({
        queryKey: ['selfloop-jobs', missionId],
        queryFn: () => selfloopApi.getSelfLoopJobs(missionId!),
        enabled: !!missionId,
        refetchInterval: 5000, // Poll every 5 seconds for updates
    });
}

/**
 * Hook for getting the latest loop state
 */
export function useLatestLoopState(missionId: string | undefined) {
    return useQuery({
        queryKey: ['loop-state', missionId],
        queryFn: () => selfloopApi.getLatestLoopState(missionId!),
        enabled: !!missionId,
        refetchInterval: 5000,
    });
}

/**
 * Hook for continuing a self-loop with next iteration
 */
export function useContinueLoop() {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: async ({
            taskId,
            goal,
            previousLoopState,
            historySummary
        }: {
            taskId: string;
            goal: string;
            previousLoopState: Parameters<typeof selfloopApi.continueLoop>[2];
            historySummary: string;
        }) => {
            const job = await selfloopApi.continueLoop(taskId, goal, previousLoopState, historySummary);
            // Auto-dispatch
            const { apiClient } = await import('../api/client');
            await apiClient.post(`/jobs/${job.id}/dispatch`);
            return job;
        },
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['jobs'] });
            queryClient.invalidateQueries({ queryKey: ['selfloop-jobs'] });
            queryClient.invalidateQueries({ queryKey: ['loop-state'] });
        },
    });
}
