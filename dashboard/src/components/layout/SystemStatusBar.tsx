import { Activity, Cpu, Network, Layers, AlertTriangle } from "lucide-react";
import type { SystemStatus } from "../../types";

interface SystemStatusBarProps {
  status: SystemStatus;
}

export function SystemStatusBar({ status }: SystemStatusBarProps) {
  const getSelfloopColor = (state: SystemStatus["selfloopState"]) => {
    switch (state) {
      case "running":
        return "text-emerald-400";
      case "degraded":
        return "text-amber-400";
      default:
        return "text-slate-500";
    }
  };

  const getSelfloopIndicator = (state: SystemStatus["selfloopState"]) => {
    switch (state) {
      case "running":
        return "bg-emerald-400";
      case "degraded":
        return "bg-amber-400 animate-pulse";
      default:
        return "bg-slate-500";
    }
  };

  return (
    <div className="bg-gradient-to-r from-slate-950 via-slate-900 to-slate-950 border-b border-slate-800 px-6 py-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-6 text-xs">
          {/* Selfloop Status */}
          <div className="flex items-center gap-2">
            <Activity className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400">Selfloop:</span>
            <div className="flex items-center gap-1.5">
              <span className={`w-2 h-2 rounded-full ${getSelfloopIndicator(status.selfloopState)}`} />
              <span className={`uppercase ${getSelfloopColor(status.selfloopState)}`}>
                {status.selfloopState}
              </span>
            </div>
          </div>

          {/* Active Model */}
          <div className="flex items-center gap-2">
            <Cpu className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400">Active Model:</span>
            <span className="text-sheratan-accent">{status.activeModel}</span>
          </div>

          {/* Mesh Nodes */}
          <div className="flex items-center gap-2">
            <Network className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400">Mesh Nodes:</span>
            <span className={status.meshNodesOnline === status.meshNodesTotal ? "text-emerald-400" : "text-amber-400"}>
              {status.meshNodesOnline}/{status.meshNodesTotal} online
            </span>
          </div>

          {/* Jobs in Queue */}
          <div className="flex items-center gap-2">
            <Layers className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400">Jobs in Queue:</span>
            <span className={status.jobsInQueue > 10 ? "text-amber-400" : "text-slate-200"}>
              {status.jobsInQueue}
            </span>
          </div>

          {/* Alerts */}
          <div className="flex items-center gap-2">
            <AlertTriangle className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-slate-400">Alerts:</span>
            <span className={status.unreadAlerts > 0 ? "text-sheratan-danger" : "text-emerald-400"}>
              {status.unreadAlerts}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-2 text-xs text-slate-500">
          <span>Profile:</span>
          <span className="text-slate-300">dev-local</span>
          <span className="mx-2">•</span>
          <span>Build:</span>
          <span className="text-slate-300">v0.4.2-dev</span>
        </div>
      </div>
    </div>
  );
}
