import { useState } from 'react';
import { ChevronDown, ChevronRight, Folder, FileText, CheckCircle, XCircle, Clock, PlayCircle } from 'lucide-react';
import { Task } from '../../api/tasks';
import { Job } from '../../types';

interface TaskHierarchyProps {
    missionId: string;
    tasks: Task[];
    jobs: Job[];
}

interface TaskWithJobs extends Task {
    jobs: Job[];
}

export function TaskHierarchy({ missionId, tasks, jobs }: TaskHierarchyProps) {
    const [expandedTasks, setExpandedTasks] = useState<Set<string>>(new Set());

    // Gruppiere Jobs nach Task
    const tasksWithJobs: TaskWithJobs[] = tasks.map(task => ({
        ...task,
        jobs: jobs.filter(job => job.missionId === task.id),
    }));

    const toggleTask = (taskId: string) => {
        const newExpanded = new Set(expandedTasks);
        if (newExpanded.has(taskId)) {
            newExpanded.delete(taskId);
        } else {
            newExpanded.add(taskId);
        }
        setExpandedTasks(newExpanded);
    };

    const getJobStatusIcon = (status: Job['status']) => {
        switch (status) {
            case 'completed':
            case 'done':
                return <CheckCircle className="w-3 h-3 text-emerald-400" />;
            case 'failed':
            case 'error':
                return <XCircle className="w-3 h-3 text-red-400" />;
            case 'working':
            case 'running':
                return <PlayCircle className="w-3 h-3 text-blue-400 animate-pulse" />;
            default:
                return <Clock className="w-3 h-3 text-slate-400" />;
        }
    };

    const getTaskStatusColor = (task: TaskWithJobs) => {
        const completed = task.jobs.filter(j => j.status === 'done' || j.status === 'completed').length;
        const failed = task.jobs.filter(j => j.status === 'error' || j.status === 'failed').length;

        if (failed > 0) return 'text-red-400';
        if (completed === task.jobs.length && task.jobs.length > 0) return 'text-emerald-400';
        if (completed > 0) return 'text-yellow-400';
        return 'text-slate-400';
    };

    if (tasks.length === 0) {
        return (
            <div className="p-4 text-center text-slate-400 text-sm">
                No tasks for this mission
            </div>
        );
    }

    return (
        <div className="space-y-1">
            {tasksWithJobs.map(task => {
                const isExpanded = expandedTasks.has(task.id);
                const statusColor = getTaskStatusColor(task);

                return (
                    <div key={task.id} className="border-l-2 border-slate-700">
                        {/* Task Row */}
                        <div
                            className="flex items-center gap-2 px-3 py-2 hover:bg-slate-800/50 cursor-pointer transition"
                            onClick={() => toggleTask(task.id)}
                        >
                            {task.jobs.length > 0 ? (
                                isExpanded ? (
                                    <ChevronDown className="w-4 h-4 text-slate-400 flex-shrink-0" />
                                ) : (
                                    <ChevronRight className="w-4 h-4 text-slate-400 flex-shrink-0" />
                                )
                            ) : (
                                <div className="w-4" />
                            )}

                            <Folder className={`w-4 h-4 ${statusColor} flex-shrink-0`} />

                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                    <span className="text-sm text-slate-200 truncate">{task.name}</span>
                                    {task.kind && (
                                        <span className="text-xs text-slate-500 bg-slate-800 px-1.5 py-0.5 rounded">
                                            {task.kind}
                                        </span>
                                    )}
                                </div>
                            </div>

                            <div className="flex items-center gap-2 text-xs text-slate-400">
                                <span>
                                    {task.jobs.filter(j => j.status === 'done' || j.status === 'completed').length}/
                                    {task.jobs.length} jobs
                                </span>
                            </div>
                        </div>

                        {/* Jobs (wenn expanded) */}
                        {isExpanded && task.jobs.length > 0 && (
                            <div className="ml-6 space-y-1">
                                {task.jobs.map(job => (
                                    <div
                                        key={job.id}
                                        className="flex items-center gap-2 px-3 py-1.5 hover:bg-slate-800/30 transition"
                                    >
                                        <FileText className="w-3 h-3 text-slate-500 flex-shrink-0 ml-4" />
                                        {getJobStatusIcon(job.status)}

                                        <div className="flex-1 min-w-0">
                                            <span className="text-xs text-slate-300 truncate block">
                                                {job.name || job.id.substring(0, 8)}
                                            </span>
                                        </div>

                                        <div className="text-xs text-slate-500">
                                            {job.type}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                );
            })}
        </div>
    );
}
