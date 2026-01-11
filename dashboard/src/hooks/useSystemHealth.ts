import { useQuery } from '@tanstack/react-query';
import { checkSystemHealth } from '../utils/healthCheck';

export const useSystemHealth = () => {
    return useQuery({
        queryKey: ['system-health'],
        queryFn: checkSystemHealth,
        refetchInterval: 30000, // Alle 30s
        retry: 2,
    });
};
