import { Network, CheckCircle2, XCircle, AlertCircle } from "lucide-react";
import { mockServiceNodes } from "../../data/mockData";
import type { ServiceNode } from "../../types";

export function DependencyMapTab() {
  const getStatusIcon = (status: ServiceNode["status"]) => {
    switch (status) {
      case "active":
        return CheckCircle2;
      case "error":
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
    }
  };

  // Build dependency tree
  const rootNodes = mockServiceNodes.filter((node) => node.dependencies.length === 0);
  const dependentNodes = mockServiceNodes.filter((node) => node.dependencies.length > 0);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-xl flex items-center gap-2">
          <Network className="w-5 h-5" />
          Service Dependency Map
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Visual representation of service dependencies and system architecture.
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
            <span className="text-slate-300">Engine</span>
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-4 h-4 rounded border ${getTypeColor("worker")}`} />
            <span className="text-slate-300">Worker</span>
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
          {/* Root Level */}
          <div className="flex justify-center mb-8">
            {rootNodes.map((node) => {
              const Icon = getStatusIcon(node.status);
              return (
                <div key={node.id} className="relative">
                  <div
                    className={`px-4 py-3 rounded-lg border-2 ${getTypeColor(node.type)} backdrop-blur-sm`}
                  >
                    <div className="flex items-center gap-2 mb-1">
                      <Icon className={`w-4 h-4 ${getStatusColor(node.status).split(" ")[0]}`} />
                      <span className="text-sm text-slate-100">{node.name}</span>
                    </div>
                    <div className="text-xs text-slate-400">{node.type}</div>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Level 1 Dependencies */}
          <div className="grid grid-cols-3 gap-6 mb-8">
            {dependentNodes
              .filter((node) => node.dependencies.includes("core-api"))
              .map((node) => {
                const Icon = getStatusIcon(node.status);
                return (
                  <div key={node.id} className="relative">
                    {/* Connection line */}
                    <div className="absolute bottom-full left-1/2 w-px h-8 bg-gradient-to-b from-sheratan-accent/40 to-transparent -translate-x-1/2" />
                    
                    <div
                      className={`px-4 py-3 rounded-lg border-2 ${getTypeColor(node.type)} backdrop-blur-sm`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <Icon className={`w-4 h-4 ${getStatusColor(node.status).split(" ")[0]}`} />
                        <span className="text-sm text-slate-100">{node.name}</span>
                      </div>
                      <div className="text-xs text-slate-400">{node.type}</div>
                    </div>
                  </div>
                );
              })}
          </div>

          {/* Level 2 Dependencies */}
          <div className="grid grid-cols-4 gap-4">
            {dependentNodes
              .filter(
                (node) =>
                  !node.dependencies.includes("core-api") &&
                  node.dependencies.length > 0
              )
              .map((node) => {
                const Icon = getStatusIcon(node.status);
                return (
                  <div key={node.id} className="relative">
                    {/* Connection line */}
                    <div className="absolute bottom-full left-1/2 w-px h-8 bg-gradient-to-b from-purple-500/40 to-transparent -translate-x-1/2" />
                    
                    <div
                      className={`px-3 py-2 rounded-lg border ${getTypeColor(node.type)} backdrop-blur-sm`}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <Icon className={`w-3 h-3 ${getStatusColor(node.status).split(" ")[0]}`} />
                        <span className="text-xs text-slate-100">{node.name}</span>
                      </div>
                      <div className="text-[10px] text-slate-400">{node.type}</div>
                      <div className="text-[10px] text-slate-500 mt-1">
                        ← {node.dependencies.join(", ")}
                      </div>
                    </div>
                  </div>
                );
              })}
          </div>
        </div>
      </div>

      {/* Service List */}
      <div className="bg-sheratan-card border border-slate-700 rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-700">
          <h3 className="text-sm">All Services</h3>
          <p className="text-xs text-slate-400 mt-0.5">{mockServiceNodes.length} total</p>
        </div>
        <div className="divide-y divide-slate-800">
          {mockServiceNodes.map((node) => {
            const Icon = getStatusIcon(node.status);
            return (
              <div key={node.id} className="px-4 py-3 hover:bg-slate-900/20 transition">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className={`w-2 h-2 rounded-full ${getStatusColor(node.status).split(" ")[0].replace("text-", "bg-")}`} />
                    <div>
                      <div className="text-sm text-slate-200">{node.name}</div>
                      <div className="text-xs text-slate-500 mt-0.5">
                        {node.dependencies.length > 0
                          ? `Depends on: ${node.dependencies.join(", ")}`
                          : "No dependencies"}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className={`px-2 py-1 rounded text-xs ${getTypeColor(node.type)}`}>
                      {node.type}
                    </span>
                    <span className={`px-2 py-1 rounded text-xs border ${getStatusColor(node.status)}`}>
                      <Icon className="w-3 h-3 inline mr-1" />
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
