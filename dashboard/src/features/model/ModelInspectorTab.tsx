import { Cpu, Zap, Thermometer, Database, FileText, Route } from "lucide-react";
import { mockModelInfo } from "../../data/mockData";
import { StatCard } from "../../components/common/StatCard";

export function ModelInspectorTab() {
  const model = mockModelInfo;

  const getTypeColor = (type: string) => {
    switch (type) {
      case "gguf":
        return "text-sheratan-accent bg-sheratan-accent/10";
      case "gpt-relay":
        return "text-emerald-400 bg-emerald-400/10";
      case "mistral":
        return "text-purple-400 bg-purple-400/10";
      default:
        return "text-slate-400 bg-slate-400/10";
    }
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-xl flex items-center gap-2">
          <Cpu className="w-5 h-5" />
          Model Inspector
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Active model metrics, token usage, performance and routing decisions.
        </p>
      </header>

      {/* Model Overview */}
      <div className="bg-sheratan-card border border-slate-700 rounded-lg p-6">
        <div className="flex items-start justify-between mb-6">
          <div>
            <h2 className="text-lg text-slate-100 mb-1">{model.name}</h2>
            <div className="flex items-center gap-2">
              <span className={`px-2 py-1 rounded text-xs ${getTypeColor(model.type)}`}>
                {model.type.toUpperCase()}
              </span>
              <span className="text-xs text-slate-500">•</span>
              <span className="text-xs text-slate-400">Routing: {model.routing}</span>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
            <span className="text-xs text-emerald-400">Active</span>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard
            label="Tokens Used"
            value={model.tokensUsed.toLocaleString()}
            icon={Database}
          />
          <StatCard
            label="Speed"
            value={`${model.tokensPerSecond} t/s`}
            icon={Zap}
            variant="success"
          />
          <StatCard
            label="Temperature"
            value={model.temperature}
            icon={Thermometer}
          />
          <StatCard
            label="Context Size"
            value={model.contextSize.toLocaleString()}
            icon={FileText}
          />
        </div>
      </div>

      {/* Performance Metrics */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-sheratan-card border border-slate-700 rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-700 flex items-center gap-2">
            <Zap className="w-4 h-4 text-sheratan-accent" />
            <h3 className="text-sm">Performance</h3>
          </div>
          <div className="p-4 space-y-4">
            <div>
              <div className="flex items-center justify-between text-sm mb-2">
                <span className="text-slate-400">Token Generation Speed</span>
                <span className="text-slate-200">{model.tokensPerSecond} tokens/sec</span>
              </div>
              <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-sheratan-accent"
                  style={{ width: `${Math.min((model.tokensPerSecond / 100) * 100, 100)}%` }}
                />
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between text-sm mb-2">
                <span className="text-slate-400">Context Utilization</span>
                <span className="text-slate-200">
                  {Math.round((model.tokensUsed / model.contextSize) * 100)}%
                </span>
              </div>
              <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-emerald-500"
                  style={{ width: `${(model.tokensUsed / model.contextSize) * 100}%` }}
                />
              </div>
            </div>
            <div>
              <div className="flex items-center justify-between text-sm mb-2">
                <span className="text-slate-400">Temperature Setting</span>
                <span className="text-slate-200">{model.temperature}</span>
              </div>
              <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-amber-500"
                  style={{ width: `${(model.temperature / 2) * 100}%` }}
                />
              </div>
            </div>
          </div>
        </div>

        <div className="bg-sheratan-card border border-slate-700 rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-700 flex items-center gap-2">
            <Route className="w-4 h-4 text-sheratan-accent" />
            <h3 className="text-sm">Routing Decision</h3>
          </div>
          <div className="p-4">
            <div className="space-y-3">
              <div>
                <span className="text-xs text-slate-400">Routing Strategy</span>
                <div className="text-sm text-slate-200 mt-1 font-mono">{model.routing}</div>
              </div>
              <div>
                <span className="text-xs text-slate-400">Model Type</span>
                <div className="text-sm text-slate-200 mt-1">{model.type}</div>
              </div>
              <div>
                <span className="text-xs text-slate-400">Execution Mode</span>
                <div className="text-sm text-slate-200 mt-1">
                  {model.type === "gguf" ? "Local GGUF" : "API Relay"}
                </div>
              </div>
              <div className="pt-3 border-t border-slate-800">
                <span className="text-xs text-slate-400">Decision Factors</span>
                <div className="mt-2 space-y-1">
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-300">Local availability</span>
                    <span className="text-emerald-400">✓</span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-300">Context size match</span>
                    <span className="text-emerald-400">✓</span>
                  </div>
                  <div className="flex items-center justify-between text-xs">
                    <span className="text-slate-300">Performance threshold</span>
                    <span className="text-emerald-400">✓</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* System Prompt */}
      <div className="bg-sheratan-card border border-slate-700 rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-700 flex items-center gap-2">
          <FileText className="w-4 h-4 text-sheratan-accent" />
          <h3 className="text-sm">System Prompt</h3>
        </div>
        <div className="p-4">
          <div className="bg-slate-950 border border-slate-800 rounded p-4 font-mono text-xs text-slate-300 leading-relaxed">
            {model.systemPrompt}
          </div>
        </div>
      </div>

      {/* Token Statistics */}
      <div className="bg-sheratan-card border border-slate-700 rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-slate-700">
          <h3 className="text-sm">Token Statistics</h3>
        </div>
        <div className="p-4">
          <div className="grid grid-cols-3 gap-4 text-center">
            <div className="bg-slate-900/50 rounded-lg p-4">
              <div className="text-2xl text-sheratan-accent mb-1">
                {model.tokensUsed.toLocaleString()}
              </div>
              <div className="text-xs text-slate-400">Total Tokens</div>
            </div>
            <div className="bg-slate-900/50 rounded-lg p-4">
              <div className="text-2xl text-emerald-400 mb-1">
                {Math.round(model.tokensUsed / 100)}
              </div>
              <div className="text-xs text-slate-400">Avg per Request</div>
            </div>
            <div className="bg-slate-900/50 rounded-lg p-4">
              <div className="text-2xl text-purple-400 mb-1">
                {model.contextSize - model.tokensUsed}
              </div>
              <div className="text-xs text-slate-400">Available Context</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
