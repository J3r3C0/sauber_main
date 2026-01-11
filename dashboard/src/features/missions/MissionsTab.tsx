import { useState, useEffect } from "react";
import { Target, Zap, CheckCircle2, AlertCircle, Eye, Plus } from "lucide-react";
import { MissionList } from "./MissionList";
import { JobTable } from "./JobTable";
import { StatCard } from "../../components/common/StatCard";
import { MissionDetailDrawer } from "../../components/common/MissionDetailDrawer";
import { LoadingSpinner } from "../../components/common/LoadingSpinner";
import { ErrorMessage } from "../../components/common/ErrorMessage";
import { CreateMissionForm } from "./CreateMissionForm";
import { QuickStartButton } from "../../components/common/QuickStartButton";
import { useMissions } from "../../hooks/useMissions";
import { useJobs } from "../../hooks/useJobs";
import { useTasks } from "../../hooks/useTasks";

export function MissionsTab() {
  const [selectedMissionId, setSelectedMissionId] = useState<string | undefined>();
  const [detailMissionId, setDetailMissionId] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);

  // React Query Hooks für echte Daten
  const { data: missions = [], isLoading: missionsLoading, error: missionsError } = useMissions();
  const { data: allJobs = [], isLoading: jobsLoading } = useJobs();
  const { data: allTasks = [] } = useTasks();

  // Auto-select erste Mission wenn geladen
  useEffect(() => {
    if (missions.length > 0 && !selectedMissionId) {
      setSelectedMissionId(missions[0].id);
    }
  }, [missions, selectedMissionId]);

  // Statistiken berechnen
  const activeMissions = missions.filter((m) => m.status === "running").length;
  const completedMissions = missions.filter((m) => m.status === "completed").length;
  const failedMissions = missions.filter((m) => m.status === "failed").length;

  // Jobs filtern nach gewählter Mission (via Tasks!)
  const filteredJobs = selectedMissionId
    ? (() => {
      // Finde Tasks der Mission
      const missionTasks = allTasks.filter(t => t.missionId === selectedMissionId);
      const taskIds = new Set(missionTasks.map(t => t.id));

      // Finde Jobs dieser Tasks  
      return allJobs.filter(j => taskIds.has(j.missionId)); // j.missionId ist task_id!
    })()
    : allJobs;

  console.log('📊 MissionsTab Debug:', {
    selectedMissionId,
    tasksForMission: allTasks.filter(t => t.missionId === selectedMissionId).length,
    totalJobs: allJobs.length,
    filteredJobs: filteredJobs.length,
  });

  const selectedMission = missions.find((m) => m.id === selectedMissionId);
  const detailMission = missions.find((m) => m.id === detailMissionId);

  // Loading State
  if (missionsLoading || jobsLoading) {
    return <LoadingSpinner />;
  }

  // Error State
  if (missionsError) {
    return <ErrorMessage error={missionsError} title="Fehler beim Laden der Missions" />;
  }

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-xl">Missions & Jobs</h1>
          <p className="text-sm text-slate-400 mt-1">
            Steuerung und Beobachtung der Sheratan-Missionen, Job-Queue und Task-Status.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <QuickStartButton />
          <button
            onClick={() => setShowCreateForm(true)}
            className="flex items-center gap-2 px-3 py-2 bg-slate-700/50 border border-slate-600/40 text-slate-300 rounded-lg hover:bg-slate-700 transition text-sm"
          >
            <Plus className="w-4 h-4" />
            New Mission
          </button>
          {selectedMission && (
            <button
              onClick={() => setDetailMissionId(selectedMissionId || null)}
              className="flex items-center gap-2 px-3 py-2 bg-sheratan-accent/10 border border-sheratan-accent/40 text-sheratan-accent rounded-lg hover:bg-sheratan-accent/20 transition text-sm"
            >
              <Eye className="w-4 h-4" />
              View Details
            </button>
          )}
        </div>
      </header>

      {/* Stats as compact tab-header style */}
      <div className="flex flex-wrap items-center gap-2 py-2 px-1 bg-sheratan-card/50 rounded-lg border border-slate-800">
        <span className="px-3 py-1 text-xs bg-slate-700/50 rounded-full">
          📋 <span className="text-slate-200">{missions.length}</span> Missions
        </span>
        <span className="px-3 py-1 text-xs bg-emerald-900/30 border border-emerald-700/30 rounded-full text-emerald-400">
          ⚡ {activeMissions} Active
        </span>
        <span className="px-3 py-1 text-xs bg-slate-700/30 rounded-full text-slate-400">
          ✅ {completedMissions} Completed
        </span>
        <span className="px-3 py-1 text-xs bg-red-900/20 border border-red-700/30 rounded-full text-red-400">
          ❌ {failedMissions} Failed
        </span>
        <span className="px-3 py-1 text-xs bg-blue-900/20 border border-blue-700/30 rounded-full text-blue-400">
          📦 {allJobs.length} Jobs ({filteredJobs.length} shown)
        </span>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="xl:col-span-1">
          <MissionList
            missions={missions}
            selectedId={selectedMissionId}
            onSelect={setSelectedMissionId}
          />
        </div>
        <div className="xl:col-span-2">
          <JobTable jobs={filteredJobs} />
        </div>
      </div>

      {detailMission && (
        <MissionDetailDrawer
          mission={detailMission}
          jobs={allJobs}
          onClose={() => setDetailMissionId(null)}
        />
      )}

      {showCreateForm && (
        <CreateMissionForm onClose={() => setShowCreateForm(false)} />
      )}
    </div>
  );
}
