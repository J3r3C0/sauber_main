import { Activity, CheckCircle, AlertTriangle, XCircle, Clock } from "lucide-react";
import { useSystemHealth } from "../../hooks/useSystemHealth";
import type { SystemHealth } from "../../utils/healthCheck";

export function HealthMonitor() {
    const { data: health, isLoading, error } = useSystemHealth();

    if (isLoading) {
        return (
            <div className="flex items-center gap-2 px-3 py-2 bg-slate-800/50 border border-slate-700 rounded-lg">
                <Activity className="w-4 h-4 text-slate-400 animate-pulse" />
                <span className="text-xs text-slate-400">Checking health...</span>
            </div>
        );
    }

    if (error || !health) {
        return (
            <div className="flex items-center gap-2 px-3 py-2 bg-red-500/10 border border-red-500/30 rounded-lg">
                <XCircle className="w-4 h-4 text-red-400" />
                <span className="text-xs text-red-400 font-medium">Health check failed</span>
            </div>
        );
    }

    return (
        <div className="space-y-2">
            {/* Overall Status */}
            <OverallStatus health={health} />

            {/* Endpoint Details */}
            <div className="grid grid-cols-2 gap-2">
                {health.endpoints.map((endpoint) => (
                    <EndpointStatus key={endpoint.endpoint} endpoint={endpoint} />
                ))}
            </div>
        </div>
    );
}

function OverallStatus({ health }: { health: SystemHealth }) {
    const getStatusConfig = () => {
        switch (health.overall) {
            case 'healthy':
                return {
                    icon: CheckCircle,
                    color: 'text-emerald-400',
                    bg: 'bg-emerald-500/10',
                    border: 'border-emerald-500/30',
                    label: 'All Systems Operational',
                };
            case 'degraded':
                return {
                    icon: AlertTriangle,
                    color: 'text-yellow-400',
                    bg: 'bg-yellow-500/10',
                    border: 'border-yellow-500/30',
                    label: 'Degraded Performance',
                };
            case 'down':
                return {
                    icon: XCircle,
                    color: 'text-red-400',
                    bg: 'bg-red-500/10',
                    border: 'border-red-500/30',
                    label: 'System Issues Detected',
                };
        }
    };

    const config = getStatusConfig();
    const Icon = config.icon;

    return (
        <div className={`flex items-center gap-2 px-3 py-2 ${config.bg} border ${config.border} rounded-lg`}>
            <Icon className={`w-4 h-4 ${config.color}`} />
            <div className="flex-1">
                <span className={`text-sm font-medium ${config.color}`}>{config.label}</span>
            </div>
        </div>
    );
}

function EndpointStatus({ endpoint }: { endpoint: SystemHealth['endpoints'][0] }) {
    const getStatusConfig = () => {
        switch (endpoint.status) {
            case 'healthy':
                return {
                    icon: CheckCircle,
                    color: 'text-emerald-400',
                    bg: 'bg-emerald-500/5',
                };
            case 'degraded':
                return {
                    icon: Clock,
                    color: 'text-yellow-400',
                    bg: 'bg-yellow-500/5',
                };
            case 'down':
                return {
                    icon: XCircle,
                    color: 'text-red-400',
                    bg: 'bg-red-500/5',
                };
        }
    };

    const config = getStatusConfig();
    const Icon = config.icon;

    return (
        <div className={`flex items-center gap-2 px-2 py-1.5 ${config.bg} rounded`}>
            <Icon className={`w-3 h-3 ${config.color} flex-shrink-0`} />
            <div className="flex-1 min-w-0">
                <div className="text-xs text-slate-300 truncate">{endpoint.endpoint}</div>
                {endpoint.responseTime && (
                    <div className="text-xs text-slate-500">{endpoint.responseTime}ms</div>
                )}
                {endpoint.error && (
                    <div className="text-xs text-red-400 truncate">{endpoint.error}</div>
                )}
            </div>
        </div>
    );
}
