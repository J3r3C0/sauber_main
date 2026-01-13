import { useState } from "react";
import { Terminal, Filter, Download, Trash2, RefreshCw } from "lucide-react";
import type { LogLevel, LogSource } from "../../types";
import { useLiveLogs } from "../../hooks/useLiveLogs";

export function LogsTab() {
  const { data: logs = [], isLoading, refetch } = useLiveLogs();
  const [selectedLevel, setSelectedLevel] = useState<LogLevel | "all">("all");
  const [selectedSource, setSelectedSource] = useState<LogSource | "all">("all");

  const filteredLogs = logs.filter((log) => {
    if (selectedLevel !== "all" && log.level !== selectedLevel) return false;
    if (selectedSource !== "all" && log.source !== selectedSource) return false;
    return true;
  });

  const getLevelColor = (level: LogLevel) => {
    switch (level) {
      case "error":
        return "text-red-400 bg-red-500/10";
      case "warn":
        return "text-amber-400 bg-amber-500/10";
      case "info":
        return "text-sheratan-accent bg-sheratan-accent/10";
      default:
        return "text-slate-400 bg-slate-500/10";
    }
  };

  const getSourceColor = (source: LogSource) => {
    const colors: Record<LogSource, string> = {
      selfloop: "text-blue-400 bg-blue-500/10",
      mesh: "text-sheratan-accent bg-sheratan-accent/10",
      trader: "text-emerald-400 bg-emerald-500/10",
      relay: "text-purple-400 bg-purple-500/10",
      core: "text-pink-400 bg-pink-500/10",
    };
    return colors[source];
  };

  const levels: (LogLevel | "all")[] = ["all", "error", "warn", "info", "debug"];
  const sources: (LogSource | "all")[] = ["all", "selfloop", "mesh", "trader", "relay", "core"];

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-xl flex items-center gap-2">
            <Terminal className="w-5 h-5" />
            Live Log Viewer
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Real-time streaming logs from Selfloop, Mesh, Trader, Relay and Core.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => refetch()}
            disabled={isLoading}
            className="flex items-center gap-2 px-3 py-2 bg-emerald-800 hover:bg-emerald-700 disabled:bg-slate-700 text-slate-100 rounded-lg text-sm transition"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
            Refresh
          </button>
          <button className="flex items-center gap-2 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm transition">
            <Download className="w-4 h-4" />
            Export
          </button>
          <button className="flex items-center gap-2 px-3 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg text-sm transition">
            <Trash2 className="w-4 h-4" />
            Clear
          </button>
        </div>
      </header>

      {/* Filters */}
      <div className="bg-sheratan-card border border-slate-700 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-3">
          <Filter className="w-4 h-4 text-slate-400" />
          <span className="text-sm text-slate-300">Filters</span>
        </div>
        <div className="flex flex-wrap gap-2">
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Level:</span>
            {levels.map((level) => (
              <button
                key={level}
                onClick={() => setSelectedLevel(level)}
                className={`px-2 py-1 rounded text-xs border transition ${selectedLevel === level
                  ? "bg-sheratan-accent/20 border-sheratan-accent text-sheratan-accent"
                  : "bg-slate-800 border-slate-700 text-slate-400 hover:bg-slate-700"
                  }`}
              >
                {level}
              </button>
            ))}
          </div>
          <div className="h-6 w-px bg-slate-700" />
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400">Source:</span>
            {sources.map((source) => (
              <button
                key={source}
                onClick={() => setSelectedSource(source)}
                className={`px-2 py-1 rounded text-xs border transition ${selectedSource === source
                  ? "bg-sheratan-accent/20 border-sheratan-accent text-sheratan-accent"
                  : "bg-slate-800 border-slate-700 text-slate-400 hover:bg-slate-700"
                  }`}
              >
                {source}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Log Console */}
      <div className="bg-black border border-slate-700 rounded-lg overflow-hidden">
        <div className="px-4 py-2 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-red-500" />
            <span className="w-3 h-3 rounded-full bg-amber-500" />
            <span className="w-3 h-3 rounded-full bg-emerald-500" />
          </div>
          <span className="text-xs text-slate-500 font-mono">
            sheratan-core/logs
          </span>
        </div>
        <div className="p-4 h-[600px] overflow-y-auto font-mono text-xs space-y-1">
          {filteredLogs.length === 0 ? (
            <div className="text-slate-500 text-center py-8">
              No logs match the current filters
            </div>
          ) : (
            filteredLogs.map((log) => (
              <div key={log.id} className="flex items-start gap-3 py-1 hover:bg-slate-900/30 px-2 -mx-2 rounded">
                <span className="text-slate-600 flex-shrink-0">
                  {new Date(log.timestamp).toLocaleTimeString()}
                </span>
                <span className={`px-1.5 py-0.5 rounded uppercase flex-shrink-0 ${getLevelColor(log.level)}`}>
                  {log.level}
                </span>
                <span className={`px-1.5 py-0.5 rounded flex-shrink-0 ${getSourceColor(log.source)}`}>
                  {log.source}
                </span>
                <span className="text-slate-300 flex-1">{log.message}</span>
              </div>
            ))
          )}
        </div>
      </div>

      <div className="flex items-center justify-between text-xs text-slate-400">
        <span>{filteredLogs.length} entries shown</span>
        <span>Auto-scroll: <span className="text-emerald-400">ON</span></span>
      </div>
    </div>
  );
}
