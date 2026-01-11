import { useQuery } from '@tanstack/react-query';
import { getLiveSystemStatus, type LiveSystemStatus } from '../api/system';

/**
 * Hook for live system status (header bar)
 * Polls every 3 seconds for near-real-time updates
 */
export function useLiveSystemStatus() {
    return useQuery<LiveSystemStatus>({
        queryKey: ['live-system-status'],
        queryFn: getLiveSystemStatus,
        refetchInterval: 3000, // 3 second polling
        staleTime: 2000,
    });
}
