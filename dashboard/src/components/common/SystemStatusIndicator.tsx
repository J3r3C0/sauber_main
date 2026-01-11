import { Activity, AlertCircle, CheckCircle } from "lucide-react";
import { useSystemStatus } from "../../hooks/useSystemStatus";

export function SystemStatusIndicator() {
    const { data: status, isLoading, error } = useSystemStatus();

    if (isLoading) {
        return (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-800/50 border border-slate-700 rounded-lg">
                <Activity className="w-4 h-4 text-slate-400 animate-pulse" />
                <span className="text-xs text-slate-400">Checking status...</span>
            </div>
        );
    }

    if (error) {
        return (
            <div className="flex items-center gap-2 px-3 py-1.5 bg-red-500/10 border border-red-500/30 rounded-lg">
                <AlertCircle className="w-4 h-4 text-red-400" />
                <div className="text-xs">
                    <span className="text-red-400 font-medium">Backend offline</span>
                    <span className="text-red-400/70 ml-2">Port 8001</span>
                </div>
            </div>
        );
    }

    return (
        <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-500/10 border border-emerald-500/30 rounded-lg">
            <div className="relative">
                <CheckCircle className="w-4 h-4 text-emerald-400" />
                <span className="absolute -top-0.5 -right-0.5 w-2 h-2 bg-emerald-400 rounded-full animate-ping" />
            </div>
            <div className="text-xs">
                <span className="text-emerald-400 font-medium">Core v2 Online</span>
                {status?.missions !== undefined && (
                    <span className="text-emerald-400/70 ml-2">{status.missions} missions</span>
                )}
            </div>
        </div>
    );
}
