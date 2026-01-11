import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { jobsApi } from '../api/jobs';

export const useJobs = () => {
    return useQuery({
        queryKey: ['jobs'],
        queryFn: jobsApi.getAll,
        refetchInterval: 10000,  // 10s statt 3s - weniger aggressiv
        refetchOnWindowFocus: false,  // Verhindert Flackern beim Tab-Wechsel
        placeholderData: (previousData) => previousData,  // Verhindert "Verschwinden" beim Refetch
    });
};

export const useJob = (id: string) => {
    return useQuery({
        queryKey: ['jobs', id],
        queryFn: () => jobsApi.getById(id),
        enabled: !!id,
    });
};

export const useDispatchJob = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: jobsApi.dispatch,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['jobs'] });
        },
    });
};

export const useSyncJob = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: jobsApi.sync,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['jobs'] });
        },
    });
};

export const useDeleteJob = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (jobId: string) => jobsApi.delete(jobId),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['jobs'] });
        },
    });
};
