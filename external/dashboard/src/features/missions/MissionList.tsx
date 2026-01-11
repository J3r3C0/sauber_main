import { useState } from "react";
import { Clock, CheckCircle2, XCircle, Circle, Trash2 } from "lucide-react";
import { Mission } from "../../types";
import { StatusPill } from "../../components/common/StatusPill";
import { useDeleteMission } from "../../hooks/useMissions";
import { useActionLog } from "../../hooks/useActionLog";

interface MissionListProps {
  missions: Mission[];
  selectedId?: string;
  onSelect: (id: string) => void;
}

export function MissionList({ missions, selectedId, onSelect }: MissionListProps) {
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const deleteMission = useDeleteMission();
  const { log } = useActionLog();

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

  const getStatusIcon = (status: Mission["status"]) => {
    switch (status) {
      case "completed":
        return CheckCircle2;
      case "running":
        return Clock;
      case "failed":
        return XCircle;
      default:
        return Circle;
    }
  };

  const handleDelete = async (e: React.MouseEvent, mission: Mission) => {
    e.stopPropagation();
    if (deleteConfirmId === mission.id) {
      try {
        log("info", `Lösche Mission: ${mission.name}...`);
        await deleteMission.mutateAsync(mission.id);
        log("success", `Mission "${mission.name}" gelöscht`);
        setDeleteConfirmId(null);
      } catch (error: any) {
        log("error", `Löschen fehlgeschlagen: ${error.message}`);
      }
    } else {
      setDeleteConfirmId(mission.id);
      log("info", "Klick nochmal zum Bestätigen");
      setTimeout(() => setDeleteConfirmId(null), 3000);
    }
  };

  return (
    <div className="bg-sheratan-card border border-slate-700 rounded-lg overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-700">
        <h3 className="text-sm">Active Missions</h3>
        <p className="text-xs text-slate-400 mt-0.5">{missions.length} total</p>
      </div>
      <div className="divide-y divide-slate-800">
        {missions.map((mission) => {
          const Icon = getStatusIcon(mission.status);
          const isSelected = mission.id === selectedId;
          const isConfirmingDelete = deleteConfirmId === mission.id;

          return (
            <div
              key={mission.id}
              className={`relative flex items-center justify-between w-full text-left px-4 py-3 hover:bg-slate-900/40 transition cursor-pointer ${isSelected ? "bg-sheratan-accent/5 border-l-2 border-sheratan-accent" : ""
                }`}
              onClick={() => onSelect(mission.id)}
            >
              {/* Left: Mission Info */}
              <div className="flex-1 min-w-0 pr-3">
                <div className="flex items-center gap-2 mb-1">
                  <Icon className="w-4 h-4 text-slate-400 flex-shrink-0" />
                  <span className="text-sm text-slate-100 truncate">{mission.name}</span>
                  <StatusPill status={mission.status} variant={getStatusVariant(mission.status)} />
                </div>

                <div className="flex items-center gap-3 text-xs text-slate-400">
                  <span>Jobs: {mission.jobsCompleted}/{mission.jobsTotal}</span>
                  <span>•</span>
                  <span className={`
                    ${mission.priority === "high" ? "text-sheratan-danger" : ""}
                    ${mission.priority === "normal" ? "text-slate-400" : ""}
                    ${mission.priority === "low" ? "text-slate-500" : ""}
                  `}>
                    {mission.priority}
                  </span>
                </div>

                {mission.status === "running" && (
                  <div className="relative h-1 bg-slate-800 rounded-full overflow-hidden mt-2">
                    <div
                      className="absolute inset-y-0 left-0 bg-sheratan-accent rounded-full transition-all"
                      style={{ width: `${mission.progress}%` }}
                    />
                  </div>
                )}
              </div>

              {/* Right: Delete Button */}
              <button
                onClick={(e) => handleDelete(e, mission)}
                disabled={deleteMission.isPending}
                className={`flex-shrink-0 p-2 rounded-lg transition ${isConfirmingDelete
                    ? "bg-red-600 text-white"
                    : "text-slate-500 hover:text-red-400 hover:bg-red-500/10"
                  }`}
                title={isConfirmingDelete ? "Nochmal klicken zum Löschen" : "Mission löschen"}
              >
                <Trash2 className="w-4 h-4" />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
