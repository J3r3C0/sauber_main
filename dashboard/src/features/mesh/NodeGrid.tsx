import { Server, Wifi, Clock } from "lucide-react";
import { MeshNode } from "../../types";
import { StatusPill } from "../../components/common/StatusPill";

interface NodeGridProps {
  nodes: MeshNode[];
  onSelectNode: (node: MeshNode) => void;
}

export function NodeGrid({ nodes, onSelectNode }: NodeGridProps) {
  const getStatusVariant = (status: MeshNode["status"]) => {
    switch (status) {
      case "online":
        return "success";
      case "degraded":
        return "warning";
      default:
        return "neutral";
    }
  };

  const getRoleColor = (role: MeshNode["role"]) => {
    switch (role) {
      case "core":
        return "text-sheratan-accent border-sheratan-accent/40 bg-sheratan-accent/10";
      case "trader":
        return "text-emerald-400 border-emerald-400/40 bg-emerald-400/10";
      case "relay":
        return "text-purple-400 border-purple-400/40 bg-purple-400/10";
      default:
        return "text-slate-400 border-slate-400/40 bg-slate-400/10";
    }
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
      {nodes.map((node) => (
        <button
          key={node.id}
          onClick={() => onSelectNode(node)}
          className="bg-sheratan-card border border-slate-700 rounded-lg p-4 hover:border-sheratan-accent/40 transition text-left"
        >
          <div className="flex items-start justify-between mb-3">
            <div className="flex items-center gap-2">
              <Server className="w-4 h-4 text-slate-400" />
              <span className="text-sm">{node.name}</span>
            </div>
            <StatusPill status={node.status} variant={getStatusVariant(node.status)} />
          </div>

          <div className="space-y-2 mb-3">
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400">Role</span>
              <span className={`px-2 py-0.5 rounded border text-xs ${getRoleColor(node.role)}`}>
                {node.role}
              </span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400">IP:Port</span>
              <span className="text-slate-300">{node.ip}:{node.port}</span>
            </div>
            <div className="flex items-center justify-between text-xs">
              <span className="text-slate-400 flex items-center gap-1">
                <Wifi className="w-3 h-3" />
                Latency
              </span>
              <span className={`${node.latency > 50 ? "text-sheratan-warning" : "text-emerald-400"}`}>
                {node.latency}ms
              </span>
            </div>
          </div>

          <div className="flex items-center justify-between pt-3 border-t border-slate-800">
            <div className="flex items-center gap-1 text-xs text-slate-400">
              <Clock className="w-3 h-3" />
              <span>{new Date(node.lastSeen).toLocaleTimeString()}</span>
            </div>
            <div className="text-xs">
              Score: <span className="text-sheratan-accent">{node.score}</span>
            </div>
          </div>
        </button>
      ))}
    </div>
  );
}
