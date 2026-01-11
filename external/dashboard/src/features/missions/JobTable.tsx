import { useState } from "react";
import { Clock, CheckCircle2, XCircle, Loader2, Play, RefreshCw, Trash2, Eye } from "lucide-react";
import { Job } from "../../types";
import { StatusPill } from "../../components/common/StatusPill";
import { useDispatchJob, useSyncJob, useDeleteJob } from "../../hooks/useJobs";
import { useActionLog } from "../../hooks/useActionLog";

interface JobTableProps {
  jobs: Job[];
}

export function JobTable({ jobs }: JobTableProps) {
  const dispatchJob = useDispatchJob();
  const syncJob = useSyncJob();
  const deleteJob = useDeleteJob();
  const { log } = useActionLog();
  const [viewResultId, setViewResultId] = useState<string | null>(null);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);

  const getStatusVariant = (status: Job["status"] | string) => {
    switch (status) {
      case "done":
      case "completed":
        return "success";
      case "working":
      case "running":
        return "info";
      case "error":
      case "failed":
        return "danger";
      default:
        return "neutral";
    }
  };

  const getStatusIcon = (status: Job["status"] | string) => {
    switch (status) {
      case "done":
      case "completed":
        return CheckCircle2;
      case "working":
      case "running":
        return Loader2;
      case "error":
      case "failed":
        return XCircle;
      default:
        return Clock;
    }
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds) return "-";
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  const handleDispatch = async (jobId: string) => {
    log("info", `Dispatche Job ${jobId.slice(0, 8)}...`);
    try {
      await dispatchJob.mutateAsync(jobId);
      log("success", `Job dispatched an Worker!`);
    } catch (error: any) {
      log("error", `Dispatch fehlgeschlagen: ${error.message}`);
    }
  };

  const handleSync = async (jobId: string) => {
    log("info", `Sync Job ${jobId.slice(0, 8)}...`);
    try {
      await syncJob.mutateAsync(jobId);
      log("success", `Job Result synchronisiert`);
    } catch (error: any) {
      log("error", `Sync fehlgeschlagen: ${error.message}`);
    }
  };

  const handleDelete = async (jobId: string) => {
    if (deleteConfirmId === jobId) {
      deleteJob.mutate(jobId);
      setDeleteConfirmId(null);
    } else {
      setDeleteConfirmId(jobId);
      setTimeout(() => setDeleteConfirmId(null), 3000);
    }
  };

  const viewingJob = jobs.find(j => j.id === viewResultId);

  return (
    <>
      <div className="bg-sheratan-card border border-slate-700 rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-700">
          <h3 className="text-sm">Job Queue & History</h3>
          <p className="text-xs text-slate-400 mt-0.5">{jobs.length} jobs tracked</p>
        </div>

        <div className="overflow-x-auto max-h-[500px] overflow-y-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-900/40 text-xs text-slate-400 uppercase tracking-wide sticky top-0">
              <tr>
                <th className="px-4 py-3 text-left">Job ID</th>
                <th className="px-4 py-3 text-left">Agent</th>
                <th className="px-4 py-3 text-left">Type</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Duration</th>
                <th className="px-4 py-3 text-left">Details</th>
                <th className="px-4 py-3 text-left">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800">
              {jobs.map((job) => {
                const Icon = getStatusIcon(job.status);
                const canDispatch = job.status === "pending" || job.status === "queued";
                const canSync = job.status === "working" || job.status === "done";
                const hasResult = job.result !== null && job.result !== undefined;
                const isConfirmingDelete = deleteConfirmId === job.id;

                // Extract error message from top-level or result
                const jobError = job.error || job.result?.error;

                return (
                  <tr key={job.id} className="hover:bg-slate-900/20 transition">
                    <td className="px-4 py-3 text-sheratan-accent font-mono text-xs">{job.id.slice(0, 8)}...</td>
                    <td className="px-4 py-3 text-slate-300">
                      <div className="flex flex-col">
                        <span className="font-medium text-slate-200">{job.payload?.name || job.payload?.task?.kind || 'Worker Job'}</span>
                        <span className="text-[10px] text-slate-500 uppercase tracking-tight">{job.agent}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-slate-800 text-xs text-slate-300">
                        {job.type}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <Icon className={`w-4 h-4 ${job.status === "working" ? "animate-spin" : ""}`} />
                        <StatusPill status={job.status} variant={getStatusVariant(job.status)} />
                      </div>
                    </td>
                    <td className="px-4 py-3 text-slate-400">{formatDuration(job.duration)}</td>
                    <td className="px-4 py-3 text-xs text-slate-500">
                      {jobError ? (
                        <span className="text-sheratan-danger" title={jobError}>{jobError}</span>
                      ) : job.status === "working" || job.status === "running" ? (
                        <span className="text-sheratan-accent">In progress...</span>
                      ) : job.status === "done" || job.status === "completed" ? (
                        <span className="text-emerald-400">Completed successfully</span>
                      ) : (
                        <span>Waiting in queue</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        {/* Dispatch */}
                        <button
                          onClick={() => handleDispatch(job.id)}
                          disabled={!canDispatch || dispatchJob.isPending}
                          title="Dispatch to worker"
                          className="p-1.5 rounded bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 transition disabled:opacity-30 disabled:cursor-not-allowed"
                        >
                          <Play className="w-3.5 h-3.5" />
                        </button>

                        {/* Sync */}
                        <button
                          onClick={() => handleSync(job.id)}
                          disabled={!canSync || syncJob.isPending}
                          title="Sync result"
                          className="p-1.5 rounded bg-blue-500/10 hover:bg-blue-500/20 text-blue-400 border border-blue-500/30 transition disabled:opacity-30 disabled:cursor-not-allowed"
                        >
                          <RefreshCw className="w-3.5 h-3.5" />
                        </button>

                        {/* View Result */}
                        <button
                          onClick={() => setViewResultId(job.id)}
                          disabled={!hasResult}
                          title="View result"
                          className="p-1.5 rounded bg-purple-500/10 hover:bg-purple-500/20 text-purple-400 border border-purple-500/30 transition disabled:opacity-30 disabled:cursor-not-allowed"
                        >
                          <Eye className="w-3.5 h-3.5" />
                        </button>

                        {/* Delete */}
                        <button
                          onClick={() => handleDelete(job.id)}
                          disabled={deleteJob.isPending}
                          title={isConfirmingDelete ? "Nochmal klicken zum Löschen" : "Job löschen"}
                          className={`p-1.5 rounded transition ${isConfirmingDelete
                            ? "bg-red-600 text-white border border-red-500"
                            : "bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30"
                            } disabled:opacity-30 disabled:cursor-not-allowed`}
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Result Modal */}
      {viewResultId && viewingJob && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setViewResultId(null)}>
          <div className="bg-sheratan-card border border-slate-600 rounded-xl max-w-2xl w-full max-h-[80vh] overflow-hidden m-4" onClick={e => e.stopPropagation()}>
            <div className="px-4 py-3 border-b border-slate-700 flex items-center justify-between">
              <h3 className="text-sm font-medium">Job Result: {viewingJob.id.slice(0, 12)}...</h3>
              <button onClick={() => setViewResultId(null)} className="text-slate-400 hover:text-white">✕</button>
            </div>
            <div className="p-4 overflow-auto max-h-[60vh]">
              <pre className="text-xs text-slate-300 bg-slate-900 p-4 rounded-lg overflow-x-auto">
                {JSON.stringify(viewingJob.result || viewingJob.payload, null, 2)}
              </pre>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
