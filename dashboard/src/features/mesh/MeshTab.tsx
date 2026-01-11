import { useState } from "react";
import { Network, Server, Activity, Globe, Wallet } from "lucide-react";
import { MeshNode } from "../../types";
import { NodeGrid } from "./NodeGrid";
import { StatCard } from "../../components/common/StatCard";
import { useQuery } from "@tanstack/react-query";
import { meshApi } from "../../api/mesh";

export function MeshTab() {
  const [selectedNode, setSelectedNode] = useState<MeshNode | null>(null);

  // Fetch real mesh workers
  const { data: nodes = [], isLoading: isLoadingNodes } = useQuery({
    queryKey: ['mesh-workers'],
    queryFn: () => meshApi.getWorkers(),
    refetchInterval: 5000, // Refresh every 5s
  });

  // Fetch ledger for "alice" (default user)
  const { data: ledger } = useQuery({
    queryKey: ['ledger-alice'],
    queryFn: () => meshApi.getLedger("alice"),
    refetchInterval: 5000,
  });

  const onlineNodes = nodes.filter((n) => n.status === "online").length;
  const avgLatency = nodes.length > 0
    ? Math.round(nodes.reduce((sum, n) => sum + (n.latency || 0), 0) / nodes.length)
    : 0;

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-xl">Mesh & Nodes</h1>
          <p className="text-sm text-slate-400 mt-1">
            Live-Übersicht über aktive Mesh-Worker, Kapazitäten und Abrechnung.
          </p>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          label="Mesh Balance (Alice)"
          value={`${ledger?.balance || 0} 🪙`}
          icon={Wallet}
          variant="warning"
        />
        <StatCard label="Total Workers" value={nodes.length} icon={Server} />
        <StatCard
          label="Online"
          value={onlineNodes}
          icon={Globe}
          variant="success"
        />
        <StatCard
          label="Avg Latency"
          value={`${avgLatency}ms`}
          icon={Activity}
          variant={avgLatency > 30 ? "warning" : "default"}
        />
      </div>

      {isLoadingNodes ? (
        <div className="p-8 text-center text-slate-400">Mesh Registry wird synchronisiert...</div>
      ) : nodes.length === 0 ? (
        <div className="p-8 bg-slate-900/50 border border-dashed border-slate-700 rounded-lg text-center">
          <p className="text-slate-400">Keine aktiven Mesh-Worker gefunden.</p>
          <p className="text-xs text-slate-500 mt-2 italic">Starte worker_loop.py um einen Worker zu registrieren.</p>
        </div>
      ) : (
        <NodeGrid nodes={nodes} onSelectNode={setSelectedNode} />
      )}

      {selectedNode && (
        <div className="bg-sheratan-card border border-slate-700 rounded-lg p-4">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm">Node Details: {selectedNode.name}</h3>
            <button
              onClick={() => setSelectedNode(null)}
              className="text-xs text-slate-400 hover:text-slate-200"
            >
              Close
            </button>
          </div>

          <div className="grid grid-cols-2 gap-4 mb-4">
            <div>
              <span className="text-xs text-slate-400">Node ID</span>
              <div className="text-sm text-slate-200 mt-1">{selectedNode.id}</div>
            </div>
            <div>
              <span className="text-xs text-slate-400">Status</span>
              <div className={`text-sm mt-1 ${selectedNode.status === 'online' ? 'text-emerald-400' : 'text-slate-400'}`}>
                {selectedNode.status.toUpperCase()}
              </div>
            </div>
            <div>
              <span className="text-xs text-slate-400">Registry Endpoint</span>
              <div className="text-sm text-slate-200 mt-1">{selectedNode.ip}</div>
            </div>
            <div>
              <span className="text-xs text-slate-400">Last Seen</span>
              <div className="text-sm text-slate-200 mt-1">
                {new Date(selectedNode.lastSeen).toLocaleTimeString()}
              </div>
            </div>
          </div>

          <div>
            <span className="text-xs text-slate-400 mb-2 block">Worker Capabilities (Cost per Job)</span>
            <div className="flex flex-wrap gap-2">
              {selectedNode.endpoints.length > 0 ? (
                selectedNode.endpoints.map((endpoint, i) => (
                  <span
                    key={i}
                    className="px-2 py-1 bg-slate-800 text-sheratan-accent text-xs rounded border border-slate-700"
                  >
                    {endpoint}
                  </span>
                ))
              ) : (
                <span className="text-xs text-slate-500">Keine Kapazitäten registriert</span>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
