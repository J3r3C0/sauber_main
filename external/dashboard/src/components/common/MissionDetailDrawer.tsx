import { useState } from "react";
import { X, Clock, CheckCircle2, Play, FileText, Settings, History, Plus, Trash2 } from "lucide-react";
import type { Mission, Job } from "../../types";
import { StatusPill } from "./StatusPill";
import { LoopStateViewer } from "./LoopStateViewer";
import { TaskHierarchy } from "./TaskHierarchy";
import { StartSelfLoopButton } from "./StartSelfLoopButton";
import { AddJobModal } from "./AddJobModal";
import { useTasks } from "../../hooks/useTasks";
import { useDeleteMission } from "../../hooks/useMissions";

interface MissionDetailDrawerProps {
  mission: Mission;
  jobs: Job[];
  onClose: () => void;
}

export function MissionDetailDrawer({ mission, jobs, onClose }: MissionDetailDrawerProps) {
  const [showAddJobModal, setShowAddJobModal] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(false);
  const { data: tasks = [] } = useTasks();
  const deleteMission = useDeleteMission();
  const getStatusVariant = (status: Mission["status"]) => {
    switch (status) {
      case "completed":
        return "success";
      case "running":
        return "info";
      case "failed":
        return "danger";
      default:
        return "neutral";
    }
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds) return "-";
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}m ${secs}s`;
  };

  const missionJobs = jobs.filter((j) => j.missionId === mission.id);

  // Extract loop state from latest completed self-loop job
  const isSelfLoopMission = mission.tags?.includes("self-loop");
  let loopState = null;
  let latestJobResult = null;

  if (isSelfLoopMission) {
    const selfLoopJobs = missionJobs
      .filter((j) => j.status === "done" && j.payload?.loop_state)
      .sort((a, b) => {
        const aTime = new Date(a.finishedAt || a.startedAt || mission.createdAt).getTime();
        const bTime = new Date(b.finishedAt || b.startedAt || mission.createdAt).getTime();
        return bTime - aTime;
      });

    const latestJob = selfLoopJobs[0];
    if (latestJob) {
      loopState = latestJob.payload?.loop_state || null;
      latestJobResult = latestJob.result || null;
    }
  }

  const timeline = [
    { event: "Mission Created", timestamp: mission.createdAt, type: "info" as const },
    ...missionJobs.map((job) => ({
      event: `Job ${job.id} ${job.status}`,
      timestamp: job.startedAt || mission.createdAt,
      type: job.status === "error" ? ("error" as const) : ("info" as const),
    })),
    { event: "Last Update", timestamp: mission.lastUpdate, type: "info" as const },
  ];

  return (
    <>
      <div className="fixed inset-0 z-50 flex items-center justify-end">
        <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

        <div className="relative w-full max-w-2xl h-full bg-sheratan-bg border-l border-slate-700 overflow-y-auto">
          {/* Header */}
          <div className="sticky top-0 bg-sheratan-card border-b border-slate-700 px-6 py-4 z-10">
            <div className="flex items-start justify-between">
              <div>
                <h2 className="text-lg text-slate-100 mb-1">{mission.name}</h2>
                <div className="flex items-center gap-2">
                  <StatusPill status={mission.status} variant={getStatusVariant(mission.status)} />
                  {mission.tags && mission.tags.length > 0 && (
                    mission.tags.map((tag) => (
                      <span
                        key={tag}
                        className="px-2 py-0.5 text-[10px] rounded-full bg-emerald-500/10 border border-emerald-500/30 text-emerald-400"
                      >
                        {tag}
                      </span>
                    ))
                  )}
                  <span className="text-xs text-slate-500">ID: {mission.id}</span>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-2 hover:bg-slate-800 rounded-lg transition"
              >
                <X className="w-5 h-5 text-slate-400" />
              </button>
            </div>

            {/* Action Buttons Row */}
            <div className="mt-3 flex items-center gap-2 flex-wrap">
              {/* Add Job Button */}
              <button
                onClick={() => setShowAddJobModal(true)}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 rounded-lg hover:bg-emerald-500/20 transition text-sm"
              >
                <Plus className="w-4 h-4" />
                Add Job
              </button>

              {/* Start Self-Loop */}
              {!isSelfLoopMission && (
                <StartSelfLoopButton
                  missionId={mission.id}
                  missionName={mission.name}
                />
              )}

              {/* Delete Mission Button */}
              <button
                onClick={() => {
                  if (deleteConfirm) {
                    deleteMission.mutate(mission.id, {
                      onSuccess: () => onClose(),
                    });
                  } else {
                    setDeleteConfirm(true);
                    setTimeout(() => setDeleteConfirm(false), 3000);
                  }
                }}
                disabled={deleteMission.isPending}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg transition text-sm ${deleteConfirm
                  ? "bg-red-600 text-white"
                  : "bg-red-500/10 border border-red-500/30 text-red-400 hover:bg-red-500/20"
                  }`}
              >
                <Trash2 className="w-4 h-4" />
                {deleteConfirm ? "Bestätigen?" : "Delete"}
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="p-6 space-y-6">
            {/* Overview */}
            <div className="bg-sheratan-card border border-slate-700 rounded-lg p-4">
              <h3 className="text-sm mb-4 flex items-center gap-2">
                <FileText className="w-4 h-4 text-sheratan-accent" />
                Overview
              </h3>
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-xs text-slate-400">Created</span>
                  <div className="text-slate-200 mt-1">
                    {new Date(mission.createdAt).toLocaleString()}
                  </div>
                </div>
                <div>
                  <span className="text-xs text-slate-400">Last Update</span>
                  <div className="text-slate-200 mt-1">
                    {new Date(mission.lastUpdate).toLocaleString()}
                  </div>
                </div>
                <div>
                  <span className="text-xs text-slate-400">Priority</span>
                  <div className="text-slate-200 mt-1 capitalize">{mission.priority}</div>
                </div>
                <div>
                  <span className="text-xs text-slate-400">Progress</span>
                  <div className="text-slate-200 mt-1">{mission.progress}%</div>
                </div>
              </div>
            </div>

            {/* Self-Loop State */}
            {isSelfLoopMission && loopState && (
              <LoopStateViewer loopState={loopState} latestJobResult={latestJobResult} />
            )}

            {isSelfLoopMission && !loopState && (
              <div className="bg-sheratan-card border border-emerald-700/50 rounded-lg p-4">
                <p className="text-sm text-slate-400 text-center">
                  🔄 Self-Loop Mission - Warte auf erste Iteration...
                </p>
              </div>
            )}

            {/* Task Hierarchy */}
            <div className="bg-sheratan-card border border-slate-700 rounded-lg overflow-hidden">
              <h3 className="text-sm px-4 py-3 border-b border-slate-700 flex items-center gap-2">
                <Settings className="w-4 h-4 text-sheratan-accent" />
                Task Hierarchy
              </h3>
              <TaskHierarchy
                missionId={mission.id}
                tasks={tasks.filter(t => t.missionId === mission.id)}
                jobs={missionJobs}
              />
            </div>

            {/* Jobs Progress */}
            <div className="bg-sheratan-card border border-slate-700 rounded-lg p-4">
              <h3 className="text-sm mb-4 flex items-center gap-2">
                <Play className="w-4 h-4 text-sheratan-accent" />
                Jobs ({mission.jobsCompleted}/{mission.jobsTotal})
              </h3>
              <div className="space-y-3">
                {missionJobs.map((job) => (
                  <div key={job.id} className="bg-slate-900/50 rounded p-3">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm text-slate-200">{job.agent}</span>
                      <StatusPill
                        status={job.status}
                        variant={
                          job.status === "done"
                            ? "success"
                            : job.status === "error"
                              ? "danger"
                              : job.status === "working"
                                ? "info"
                                : "neutral"
                        }
                      />
                    </div>
                    <div className="flex items-center gap-3 text-xs text-slate-400">
                      <span>Type: {job.type}</span>
                      <span>•</span>
                      <span>Duration: {formatDuration(job.duration)}</span>
                    </div>
                    {job.error && (
                      <div className="mt-2 text-xs text-red-400 bg-red-500/10 rounded px-2 py-1">
                        {job.error}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Timeline */}
            <div className="bg-sheratan-card border border-slate-700 rounded-lg p-4">
              <h3 className="text-sm mb-4 flex items-center gap-2">
                <History className="w-4 h-4 text-sheratan-accent" />
                Timeline
              </h3>
              <div className="space-y-3">
                {timeline.map((item, i) => (
                  <div key={i} className="flex gap-3">
                    <div className="flex flex-col items-center">
                      <div
                        className={`w-2 h-2 rounded-full ${item.type === "error" ? "bg-red-400" : "bg-sheratan-accent"
                          }`}
                      />
                      {i < timeline.length - 1 && (
                        <div className="w-px h-full bg-slate-800 mt-1" />
                      )}
                    </div>
                    <div className="flex-1 pb-4">
                      <div className="text-sm text-slate-200">{item.event}</div>
                      <div className="text-xs text-slate-500 mt-0.5">
                        {new Date(item.timestamp).toLocaleString()}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Parameters */}
            <div className="bg-sheratan-card border border-slate-700 rounded-lg p-4">
              <h3 className="text-sm mb-4 flex items-center gap-2">
                <Settings className="w-4 h-4 text-sheratan-accent" />
                Parameters
              </h3>
              <div className="bg-slate-950 border border-slate-800 rounded p-3 font-mono text-xs text-slate-300">
                <pre>{JSON.stringify({ mission }, null, 2)}</pre>
              </div>
            </div>

            {/* Logs Snippet */}
            <div className="bg-sheratan-card border border-slate-700 rounded-lg p-4">
              <h3 className="text-sm mb-4 flex items-center gap-2">
                <Clock className="w-4 h-4 text-sheratan-accent" />
                Recent Logs
              </h3>
              <div className="bg-black border border-slate-800 rounded p-3 font-mono text-xs space-y-1 max-h-48 overflow-y-auto">
                <div className="text-slate-400">
                  <span className="text-slate-600">[14:22:35]</span>{" "}
                  <span className="text-sheratan-accent">INFO</span> Mission {mission.id} processing...
                </div>
                <div className="text-slate-400">
                  <span className="text-slate-600">[14:22:10]</span>{" "}
                  <span className="text-emerald-400">SUCCESS</span> Job completed: {missionJobs[0]?.id}
                </div>
                <div className="text-slate-400">
                  <span className="text-slate-600">[14:21:58]</span>{" "}
                  <span className="text-sheratan-accent">INFO</span> Starting next job in queue
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Add Job Modal */}
      {
        showAddJobModal && (
          <AddJobModal
            missionId={mission.id}
            missionName={mission.name}
            onClose={() => setShowAddJobModal(false)}
          />
        )
      }
    </>
  );
}
