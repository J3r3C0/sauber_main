import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { missionsApi } from '../api/missions';
import type { Mission } from '../types';

export const useMissions = () => {
    return useQuery({
        queryKey: ['missions'],
        queryFn: missionsApi.getAll,
        refetchInterval: 5000, // Auto-refresh alle 5s
    });
};

export const useMission = (id: string) => {
    return useQuery({
        queryKey: ['missions', id],
        queryFn: () => missionsApi.getById(id),
        enabled: !!id,
    });
};

export const useCreateMission = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: missionsApi.create,
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['missions'] });
        },
    });
};

export const useDeleteMission = () => {
    const queryClient = useQueryClient();

    return useMutation({
        mutationFn: (id: string) => missionsApi.delete(id),
        onSuccess: () => {
            queryClient.invalidateQueries({ queryKey: ['missions'] });
            queryClient.invalidateQueries({ queryKey: ['tasks'] });
            queryClient.invalidateQueries({ queryKey: ['jobs'] });
        },
    });
};
