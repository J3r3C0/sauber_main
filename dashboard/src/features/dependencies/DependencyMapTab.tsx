import { Network, CheckCircle2, XCircle, AlertCircle } from "lucide-react";
import { useSystemHealth } from "../../hooks/useSystemHealth";
import { LoadingSpinner } from "../../components/common/LoadingSpinner";
import { ErrorMessage } from "../../components/common/ErrorMessage";
import type { ServiceNode } from "../../types";

export function DependencyMapTab() {
  const { data: liveServices = [], isLoading, error } = useSystemHealth() as { data: ServiceNode[], isLoading: boolean, error: any };

  const getStatusIcon = (status: ServiceNode["status"]) => {
    switch (status) {
      case "active":
        return CheckCircle2;
      case "error":
      case "down":
        return XCircle;
      default:
        return AlertCircle;
    }
  };

  const getStatusColor = (status: ServiceNode["status"]) => {
    switch (status) {
      case "active":
        return "text-emerald-400 border-emerald-500/40 bg-emerald-500/10";
      case "error":
      case "down":
        return "text-red-400 border-red-500/40 bg-red-500/10";
      default:
        return "text-slate-400 border-slate-500/40 bg-slate-500/10";
    }
  };

  const getTypeColor = (type: ServiceNode["type"]) => {
    switch (type) {
      case "core":
        return "bg-sheratan-accent/20 border-sheratan-accent";
      case "engine":
        return "bg-purple-500/20 border-purple-500";
      case "worker":
        return "bg-emerald-500/20 border-emerald-500";
      case "relay":
        return "bg-amber-500/20 border-amber-500";
      default:
        return "bg-slate-500/20 border-slate-500";
    }
  };

  if (isLoading) return <LoadingSpinner />;
  if (error) return <ErrorMessage error={error} title="Fehler beim Laden der Health-Daten" />;

  // Build dependency tree from live data
  const rootNodes = liveServices.filter((node) => node.dependencies.length === 0);
  const dependentNodes = liveServices.filter((node) => node.dependencies.length > 0);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-xl flex items-center gap-2">
          <Network className="w-5 h-5" />
          Live Service Map
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Echtzeit-Status der Sheratan-Infrastruktur auf Basis von Port-Verfügbarkeit.
        </p>
      </header>

      {/* Legend */}
      <div className="bg-sheratan-card border border-slate-700 rounded-lg p-4">
        <h3 className="text-sm mb-3">Legend</h3>
        <div className="flex flex-wrap gap-4 text-xs">
          <div className="flex items-center gap-2">
            <div className={`w-4 h-4 rounded border ${getTypeColor("core")}`} />
            <span className="text-slate-300">Core</span>
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-4 h-4 rounded border ${getTypeColor("engine")}`} />
            <span className="text-slate-300">Service / Host</span>
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-4 h-4 rounded border ${getTypeColor("relay")}`} />
            <span className="text-slate-300">Relay</span>
          </div>
        </div>
      </div>

      {/* Dependency Graph */}
      <div className="bg-sheratan-card border border-slate-700 rounded-lg p-6 overflow-x-auto">
        <div className="min-w-[800px]">
          {/* Root Level (Core API) */}
          <div className="flex justify-center mb-8">
            {rootNodes.map((node) => {
              const Icon = getStatusIcon(node.status);
              return (
                <div key={node.id} className="relative">
                  <div
                    className={`px-6 py-4 rounded-lg border-2 ${getTypeColor(node.type)} backdrop-blur-sm shadow-lg shadow-sheratan-accent/5`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <Icon className={`w-5 h-5 ${getStatusColor(node.status).split(" ")[0]}`} />
                      <span className="text-base font-medium text-slate-100">{node.name}</span>
                    </div>
                    <div className="text-xs text-slate-400 uppercase tracking-wider">{node.type}</div>
                    <div className="text-[10px] text-sheratan-accent mt-1">Uptime: {node.uptime}</div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Level 1 Dependencies (Relay, Broker, etc) */}
          <div className="grid grid-cols-4 gap-6">
            {dependentNodes.map((node) => {
              const Icon = getStatusIcon(node.status);
              return (
                <div key={node.id} className="relative">
                  {/* Connection line */}
                  <div className="absolute bottom-full left-1/2 w-px h-8 bg-gradient-to-b from-slate-700 to-transparent -translate-x-1/2" />

                  <div
                    className={`px-4 py-3 rounded-lg border-2 ${getTypeColor(node.type)} backdrop-blur-sm transition-all hover:scale-[1.02]`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <Icon className={`w-4 h-4 ${getStatusColor(node.status).split(" ")[0]}`} />
                      <span className="text-sm text-slate-100">{node.name}</span>
                    </div>
                    <div className="flex items-center justify-between mt-1">
                      <div className="text-xs text-slate-400 capitalize">{node.type}</div>
                      <div className="text-[10px] text-slate-500">Port {node.port}</div>
                    </div>
                    <div className="text-[9px] text-slate-500 mt-2 flex items-center gap-1">
                      <span className="w-1 h-1 rounded-full bg-slate-600"></span>
                      Status: {node.status}
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Service List Table */}
      <div className="bg-sheratan-card border border-slate-700 rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-700 flex justify-between items-center">
          <div>
            <h3 className="text-sm font-medium">Active Services</h3>
            <p className="text-xs text-slate-400 mt-0.5">{liveServices.filter(s => s.status === 'active').length} of {liveServices.length} online</p>
          </div>
          <div className="bg-slate-800/50 px-2 py-1 rounded text-[10px] text-slate-400 border border-slate-700">
            Auto-refresh: 30s
          </div>
        </div>
        <div className="divide-y divide-slate-800">
          {liveServices.map((node) => {
            const Icon = getStatusIcon(node.status);
            return (
              <div key={node.id} className="px-4 py-3 hover:bg-slate-900/40 transition">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-2 h-2 rounded-full ${getStatusColor(node.status).split(" ")[0].replace("text-", "bg-")}`} />
                    <div>
                      <div className="text-sm font-medium text-slate-200">{node.name}</div>
                      <div className="text-xs text-slate-500 mt-0.5">
                        UPTIME: <span className="text-slate-400">{node.uptime}</span> | PORT: <span className="text-slate-400">{node.port}</span>
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold border ${getTypeColor(node.type)}`}>
                      {node.type}
                    </span>
                    <span className={`px-2 py-0.5 rounded text-[10px] uppercase font-bold border ${getStatusColor(node.status)}`}>
                      {node.status}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
