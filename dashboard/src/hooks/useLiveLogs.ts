import { useQuery } from '@tanstack/react-query';
import { getLiveLogsFromJobs } from '../api/logs';

/**
 * Hook for live logs from job results
 * Polls every 5 seconds for updates
 */
export function useLiveLogs() {
    return useQuery({
        queryKey: ['live-logs'],
        queryFn: getLiveLogsFromJobs,
        refetchInterval: 5000, // 5 second polling
        staleTime: 4000,
    });
}
