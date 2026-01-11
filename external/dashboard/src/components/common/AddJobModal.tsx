import { useState, useEffect } from "react";
import { Plus, X, Play, FileCode, FolderTree, Cpu, AlertTriangle } from "lucide-react";
import { useTasks } from "../../hooks/useTasks";
import { apiClient } from "../../api/client";
import { useQueryClient } from "@tanstack/react-query";
import { useActionLog } from "../../hooks/useActionLog";

interface AddJobModalProps {
    missionId: string;
    missionName?: string;
    onClose: () => void;
}

const JOB_KINDS = [
    { value: "list_files", label: "List Files", icon: FolderTree, description: "Dateien im Projekt auflisten" },
    { value: "read_file", label: "Read File", icon: FileCode, description: "Datei-Inhalt lesen" },
    { value: "agent_plan", label: "Agent Plan", icon: Cpu, description: "LLM generiert einen Plan" },
    { value: "llm_call", label: "LLM Call", icon: Cpu, description: "Direkter LLM-Aufruf" },
];

export function AddJobModal({ missionId, missionName, onClose }: AddJobModalProps) {
    const queryClient = useQueryClient();
    const { data: allTasks = [], isLoading: tasksLoading } = useTasks();
    const { log } = useActionLog();

    const missionTasks = allTasks.filter(t => t.missionId === missionId);

    const [selectedTaskId, setSelectedTaskId] = useState<string>("");
    const [jobKind, setJobKind] = useState("list_files");
    const [jobName, setJobName] = useState("");
    const [paramsJson, setParamsJson] = useState(`{
  "root": "/workspace/project",
  "patterns": ["**/*.py"]
}`);
    const [autoDispatch, setAutoDispatch] = useState(true);
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [error, setError] = useState<string | null>(null);

    // Auto-select first task when tasks load
    useEffect(() => {
        if (missionTasks.length > 0 && !selectedTaskId) {
            setSelectedTaskId(missionTasks[0].id);
        }
    }, [missionTasks, selectedTaskId]);

    // Update params template when job kind changes
    const updateParamsTemplate = (kind: string) => {
        setJobKind(kind);
        switch (kind) {
            case "list_files":
                setParamsJson(`{
  "root": "/workspace/project",
  "patterns": ["**/*.py"]
}`);
                break;
            case "read_file":
                setParamsJson(`{
  "root": "/workspace/project",
  "rel_path": "main.py"
}`);
                break;
            case "agent_plan":
                setParamsJson(`{
  "user_prompt": "Analyze this project",
  "project_root": "/workspace/project"
}`);
                break;
            case "llm_call":
                setParamsJson(`{
  "prompt": "Describe what this code does"
}`);
                break;
        }
    };

    const handleSubmit = async () => {
        // If no task exists, create one first
        let taskId = selectedTaskId;

        if (!taskId && missionTasks.length === 0) {
            setError(null);
            setIsSubmitting(true);
            try {
                log("info", "Kein Task vorhanden - erstelle automatisch...");
                // Use correct endpoint: /missions/{missionId}/tasks
                const taskResponse = await apiClient.post(`/missions/${missionId}/tasks`, {
                    name: jobName || `Task für ${missionName || 'Mission'}`,
                    description: 'Auto-created task for job',
                    kind: 'analysis',
                    params: {},
                });
                log("success", `Task erstellt: ${taskResponse.data.id.slice(0, 8)}`);
                queryClient.invalidateQueries({ queryKey: ["tasks"] });
                taskId = taskResponse.data.id;
            } catch (err: any) {
                log("error", `Auto-Task fehlgeschlagen: ${err.message}`);
                setError(`Task-Erstellung fehlgeschlagen: ${err.response?.data?.detail || err.message}`);
                setIsSubmitting(false);
                return;
            }
        }

        if (!taskId) {
            setError("Bitte wähle eine Task aus oder erstelle eine neue");
            return;
        }

        let params;
        try {
            params = JSON.parse(paramsJson);
        } catch {
            setError("Ungültiges JSON in Params");
            return;
        }

        setIsSubmitting(true);
        setError(null);

        try {
            log("info", `Erstelle Job (${jobKind})...`);

            // Create job via correct endpoint: /tasks/{taskId}/jobs
            const jobPayload = {
                payload: {
                    response_format: "lcp",
                    task: {
                        kind: jobKind,
                        params: params,
                    },
                },
            };

            const response = await apiClient.post(`/tasks/${taskId}/jobs`, jobPayload);
            const newJobId = response.data.id;
            log("success", `Job erstellt: ${newJobId.slice(0, 8)}`);

            // Auto-dispatch if enabled
            if (autoDispatch && newJobId) {
                log("info", "Dispatche Job...");
                await apiClient.post(`/jobs/${newJobId}/dispatch`);
                log("success", "Job dispatched!");
            }

            // Invalidate queries
            queryClient.invalidateQueries({ queryKey: ["jobs"] });
            queryClient.invalidateQueries({ queryKey: ["tasks"] });

            onClose();
        } catch (err: any) {
            console.error("Failed to create job:", err);
            log("error", `Job-Erstellung fehlgeschlagen: ${err.message}`);
            setError(err.response?.data?.detail || err.message || "Fehler beim Erstellen");
        } finally {
            setIsSubmitting(false);
        }
    };

    const noTasksExist = missionTasks.length === 0 && !tasksLoading;

    return (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={onClose}>
            <div
                className="bg-sheratan-card border border-slate-600 rounded-xl w-full max-w-lg m-4 overflow-hidden"
                onClick={e => e.stopPropagation()}
            >
                {/* Header */}
                <div className="px-5 py-4 border-b border-slate-700 flex items-center justify-between">
                    <div className="flex items-center gap-2">
                        <Plus className="w-5 h-5 text-emerald-400" />
                        <h3 className="text-base font-medium">Neuen Job erstellen</h3>
                    </div>
                    <button onClick={onClose} className="text-slate-400 hover:text-white p-1">
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Content */}
                <div className="p-5 space-y-4">
                    {/* Info wenn keine Tasks existieren */}
                    {noTasksExist && (
                        <div className="p-3 bg-amber-500/10 border border-amber-500/30 rounded-lg flex items-start gap-2">
                            <AlertTriangle className="w-4 h-4 text-amber-400 mt-0.5 flex-shrink-0" />
                            <div className="text-sm text-amber-200">
                                <strong>Kein Task vorhanden.</strong> Ein Task wird automatisch erstellt wenn du den Job erstellst.
                            </div>
                        </div>
                    )}

                    {/* Task Selection (wenn Tasks existieren) */}
                    {!noTasksExist && (
                        <div>
                            <label className="block text-xs text-slate-400 mb-1.5">Task</label>
                            <select
                                value={selectedTaskId}
                                onChange={e => setSelectedTaskId(e.target.value)}
                                className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none"
                            >
                                {missionTasks.map(task => (
                                    <option key={task.id} value={task.id}>{task.name}</option>
                                ))}
                            </select>
                        </div>
                    )}

                    {/* Job Name */}
                    <div>
                        <label className="block text-xs text-slate-400 mb-1.5">Job Name</label>
                        <input
                            type="text"
                            value={jobName}
                            onChange={e => setJobName(e.target.value)}
                            placeholder="z.B. Analyze main.py"
                            className="w-full bg-slate-800 border border-slate-600 rounded-lg px-3 py-2 text-sm focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none"
                        />
                    </div>

                    {/* Job Kind */}
                    <div>
                        <label className="block text-xs text-slate-400 mb-1.5">Job Typ</label>
                        <div className="grid grid-cols-2 gap-2">
                            {JOB_KINDS.map(kind => {
                                const Icon = kind.icon;
                                const isSelected = jobKind === kind.value;
                                return (
                                    <button
                                        key={kind.value}
                                        onClick={() => updateParamsTemplate(kind.value)}
                                        className={`flex items-center gap-2 p-2.5 rounded-lg border text-left transition ${isSelected
                                            ? "bg-emerald-500/20 border-emerald-500 text-emerald-400"
                                            : "bg-slate-800 border-slate-600 text-slate-300 hover:border-slate-500"
                                            }`}
                                    >
                                        <Icon className="w-4 h-4 flex-shrink-0" />
                                        <div>
                                            <div className="text-sm font-medium">{kind.label}</div>
                                            <div className="text-xs text-slate-500">{kind.description}</div>
                                        </div>
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    {/* Params JSON */}
                    <div>
                        <label className="block text-xs text-slate-400 mb-1.5">Parameters (JSON)</label>
                        <textarea
                            value={paramsJson}
                            onChange={e => setParamsJson(e.target.value)}
                            rows={5}
                            className="w-full bg-slate-900 border border-slate-600 rounded-lg px-3 py-2 text-xs font-mono focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none"
                        />
                    </div>

                    {/* Auto-Dispatch */}
                    <label className="flex items-center gap-2 cursor-pointer">
                        <input
                            type="checkbox"
                            checked={autoDispatch}
                            onChange={e => setAutoDispatch(e.target.checked)}
                            className="w-4 h-4 rounded bg-slate-800 border-slate-600 text-emerald-500 focus:ring-emerald-500"
                        />
                        <span className="text-sm text-slate-300">Automatisch dispatchen</span>
                    </label>

                    {/* Error */}
                    {error && (
                        <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-sm text-red-400">
                            {error}
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="px-5 py-4 border-t border-slate-700 flex items-center justify-end gap-3">
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-sm text-slate-400 hover:text-white transition"
                    >
                        Abbrechen
                    </button>
                    <button
                        onClick={handleSubmit}
                        disabled={isSubmitting}
                        className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-medium rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {isSubmitting ? (
                            <>Erstelle...</>
                        ) : (
                            <>
                                <Play className="w-4 h-4" />
                                {noTasksExist ? "Task + Job erstellen" : "Job erstellen"}
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    );
}
