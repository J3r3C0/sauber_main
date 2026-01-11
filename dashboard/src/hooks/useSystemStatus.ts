import { useQuery } from '@tanstack/react-query';
import { systemApi } from '../api/system';

export const useSystemStatus = () => {
    return useQuery({
        queryKey: ['system-status'],
        queryFn: systemApi.getStatus,
        refetchInterval: 10000, // Alle 10s prüfen
        retry: 3,
    });
};
