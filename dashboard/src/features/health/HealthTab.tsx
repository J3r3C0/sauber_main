import { Server, Cpu, HardDrive, AlertCircle, CheckCircle2, Clock } from "lucide-react";
import { StatCard } from "../../components/common/StatCard";
import { StatusPill } from "../../components/common/StatusPill";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { useQuery } from "@tanstack/react-query";
import { getSystemMetrics, getSystemHealth } from "../../api/system";
import { useState, useEffect } from "react";

export function HealthTab() {
  const { data: metrics = { cpu: 0, memory: 0, queueLength: 0, errorRate: 0 }, isLoading: isLoadingMetrics } = useQuery({
    queryKey: ['system-metrics'],
    queryFn: getSystemMetrics,
    refetchInterval: 3000,
  });

  const { data: health = [], isLoading: isLoadingHealth } = useQuery({
    queryKey: ['system-health'],
    queryFn: getSystemHealth,
    refetchInterval: 5000,
  });

  const [history, setHistory] = useState<any[]>([]);

  useEffect(() => {
    if (metrics) {
      setHistory(prev => {
        const newEntry = {
          time: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }),
          cpu: metrics.cpu,
          memory: metrics.memory,
        };
        const updated = [...prev, newEntry];
        return updated.slice(-20); // Keep last 20 entries
      });
    }
  }, [metrics]);

  const servicesUp = health.filter((s: any) => s.status === "up").length;
  const servicesDown = health.filter((s: any) => s.status === "down").length;

  const getStatusVariant = (status: string) => {
    switch (status) {
      case "up": return "success";
      case "degraded": return "warning";
      default: return "danger";
    }
  };

  const getStatusIcon = (status: string) => {
    return status === "up" ? CheckCircle2 : AlertCircle;
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-xl">System Health & Status</h1>
        <p className="text-sm text-slate-400 mt-1">
          Service-Status, System-Metriken, Ports und Performance-Charts (Live).
        </p>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <StatCard
          label="CPU Usage"
          value={`${Math.round(metrics.cpu)}%`}
          icon={Cpu}
          variant={metrics.cpu > 70 ? "warning" : "default"}
        />
        <StatCard
          label="Memory"
          value={`${Math.round(metrics.memory)}%`}
          icon={HardDrive}
          variant={metrics.memory > 80 ? "danger" : "default"}
        />
        <StatCard
          label="Pending/Running"
          value={metrics.queueLength}
          icon={Clock}
        />
        <StatCard
          label="Job Error Rate"
          value={`${metrics.errorRate}%`}
          icon={AlertCircle}
          variant={metrics.errorRate > 5 ? "danger" : "success"}
        />
      </div>

      <div className="bg-sheratan-card border border-slate-700 rounded-lg p-4">
        <h3 className="text-sm mb-4">Real-time Metrics (Last 20 Samples)</h3>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={history}>
            <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
            <XAxis dataKey="time" stroke="#64748b" style={{ fontSize: 9 }} />
            <YAxis stroke="#64748b" style={{ fontSize: 11 }} />
            <Tooltip
              contentStyle={{
                backgroundColor: "#0f172a",
                border: "1px solid #334155",
                borderRadius: "6px",
                fontSize: 12,
              }}
            />
            <Area
              type="monotone"
              dataKey="cpu"
              stroke="#00C3D4"
              fill="#00C3D433"
              strokeWidth={2}
              isAnimationActive={false}
            />
            <Area
              type="monotone"
              dataKey="memory"
              stroke="#10b981"
              fill="#10b98133"
              strokeWidth={2}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Services Status */}
        <div className="bg-sheratan-card border border-slate-700 rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-700">
            <h3 className="text-sm">Services & Port Checks</h3>
            <div className="flex items-center gap-3 text-xs text-slate-400 mt-1">
              <span className="text-emerald-400">{servicesUp} ACTIVE</span>
              <span className="text-red-400">{servicesDown} DOWN</span>
            </div>
          </div>
          <div className="divide-y divide-slate-800">
            {isLoadingHealth ? (
              <div className="p-4 text-center text-xs text-slate-500 italic">Checking ports...</div>
            ) : health.map((service: any) => {
              const Icon = getStatusIcon(service.status);
              return (
                <div key={service.name} className="px-4 py-3 hover:bg-slate-900/20 transition">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <Icon className="w-4 h-4 text-slate-400" />
                      <span className="text-sm text-slate-200">{service.name}</span>
                    </div>
                    <StatusPill status={service.status} variant={getStatusVariant(service.status)} />
                  </div>
                  <div className="flex items-center gap-4 text-xs text-slate-400 ml-6">
                    <span>Port: <span className="text-sheratan-accent">{service.port}</span></span>
                    <span>•</span>
                    <span>Status: {service.status.toUpperCase()}</span>
                    <span>•</span>
                    <span>Checked: {new Date(service.lastCheck).toLocaleTimeString()}</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Port Configuration */}
        <div className="bg-sheratan-card border border-slate-700 rounded-lg overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-700">
            <h3 className="text-sm">Port Configuration</h3>
            <p className="text-xs text-slate-400 mt-0.5">Active service ports</p>
          </div>
          <div className="p-4 space-y-3">
            <div className="flex items-center justify-between p-3 bg-slate-900/40 rounded border border-slate-800">
              <div>
                <div className="text-sm text-slate-200">Core API</div>
                <div className="text-xs text-slate-400 mt-0.5">HTTP REST API</div>
              </div>
              <div className="text-sheratan-accent">:7007</div>
            </div>
            <div className="flex items-center justify-between p-3 bg-slate-900/40 rounded border border-slate-800">
              <div>
                <div className="text-sm text-slate-200">Mesh Discovery</div>
                <div className="text-xs text-slate-400 mt-0.5">UDP Broadcast</div>
              </div>
              <div className="text-sheratan-accent">:9001</div>
            </div>
            <div className="flex items-center justify-between p-3 bg-slate-900/40 rounded border border-slate-800">
              <div>
                <div className="text-sm text-slate-200">Trader Engine</div>
                <div className="text-xs text-slate-400 mt-0.5">WebSocket + REST</div>
              </div>
              <div className="text-sheratan-accent">:8080</div>
            </div>
            <div className="flex items-center justify-between p-3 bg-slate-900/40 rounded border border-slate-800">
              <div>
                <div className="text-sm text-slate-200">Relay Inbound</div>
                <div className="text-xs text-slate-400 mt-0.5">TCP Stream</div>
              </div>
              <div className="text-sheratan-accent">:9100</div>
            </div>
            <div className="flex items-center justify-between p-3 bg-slate-900/40 rounded border border-slate-800">
              <div>
                <div className="text-sm text-slate-200">Relay Outbound</div>
                <div className="text-xs text-slate-400 mt-0.5">TCP Stream</div>
              </div>
              <div className="text-sheratan-accent">:9101</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
