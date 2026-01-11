import { apiClient } from './client';
import type { LogEntry, LogLevel, LogSource } from '../types';

interface JobApiResponse {
    id: string;
    task_id: string;
    status: string;
    created_at?: string;
    updated_at?: string;
    result?: {
        text?: string;
        output?: string;
        error?: string;
        [key: string]: any;
    };
    payload?: any;
}

/**
 * Extract log entries from job results
 * Transforms job data into log format for the LogsTab
 */
export const getLiveLogsFromJobs = async (): Promise<LogEntry[]> => {
    try {
        const response = await apiClient.get<JobApiResponse[]>('/jobs');
        const jobs = response.data || [];

        const logs: LogEntry[] = [];

        jobs.forEach((job, index) => {
            // Determine log level based on job status
            let level: LogLevel = 'info';
            if (job.status === 'failed' || job.result?.error) {
                level = 'error';
            } else if (job.status === 'running' || job.status === 'working') {
                level = 'warn';
            } else if (job.status === 'done') {
                level = 'info';
            } else {
                level = 'debug';
            }

            // Determine source based on job type or task
            let source: LogSource = 'core';
            const payload = job.payload || {};
            if (payload.job_type === 'sheratan_selfloop' || payload.loop_state) {
                source = 'selfloop';
            } else if (payload.task?.includes('relay') || payload.action?.includes('relay')) {
                source = 'relay';
            }

            // Create log entry for job creation
            logs.push({
                id: `${job.id}-created`,
                timestamp: job.created_at || new Date().toISOString(),
                level: 'debug',
                source,
                message: `Job created: ${job.id.substring(0, 8)}... [${job.status}]`,
            });

            // Create log entry for job result if available
            if (job.result) {
                const resultText = job.result.text || job.result.output ||
                    (job.result.error ? `Error: ${job.result.error}` : JSON.stringify(job.result).substring(0, 100));

                logs.push({
                    id: `${job.id}-result`,
                    timestamp: job.updated_at || job.created_at || new Date().toISOString(),
                    level,
                    source,
                    message: `[${job.id.substring(0, 8)}] ${resultText.substring(0, 200)}${resultText.length > 200 ? '...' : ''}`,
                });
            }

            // Add error log if job failed
            if (job.status === 'failed' && job.result?.error) {
                logs.push({
                    id: `${job.id}-error`,
                    timestamp: job.updated_at || new Date().toISOString(),
                    level: 'error',
                    source,
                    message: `❌ Job failed: ${job.result.error}`,
                });
            }
        });

        // Sort by timestamp, newest first
        logs.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

        return logs.slice(0, 100); // Limit to 100 entries
    } catch (error) {
        console.error('Failed to fetch live logs:', error);
        return [{
            id: 'error-fetch',
            timestamp: new Date().toISOString(),
            level: 'error',
            source: 'core',
            message: `Failed to fetch logs: ${error}`,
        }];
    }
};
