import { useQuery } from '@tanstack/react-query';
import { tasksApi, Task } from '../api/tasks';

export const useTasks = () => {
    return useQuery({
        queryKey: ['tasks'],
        queryFn: tasksApi.getAll,
        refetchInterval: 10000,
        placeholderData: (previousData) => previousData,
    });
};

export const useMissionTasks = (missionId: string | null) => {
    return useQuery({
        queryKey: ['tasks', 'mission', missionId],
        queryFn: () => missionId ? tasksApi.getByMissionId(missionId) : Promise.resolve([]),
        enabled: !!missionId,
        refetchInterval: 10000,
    });
};
