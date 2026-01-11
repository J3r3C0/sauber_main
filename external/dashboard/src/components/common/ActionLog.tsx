import { useActionLog, LogLevel } from "../../hooks/useActionLog";
import { Info, CheckCircle2, XCircle, AlertTriangle, Trash2 } from "lucide-react";

const levelConfig: Record<LogLevel, { icon: typeof Info; color: string }> = {
    info: { icon: Info, color: "text-blue-400" },
    success: { icon: CheckCircle2, color: "text-emerald-400" },
    error: { icon: XCircle, color: "text-red-400" },
    warning: { icon: AlertTriangle, color: "text-amber-400" },
};

export function ActionLog() {
    const { logs, clear } = useActionLog();

    if (logs.length === 0) {
        return (
            <div className="bg-sheratan-card border border-slate-700 rounded-lg p-3">
                <div className="text-xs text-slate-500 text-center">
                    Keine Aktionen - klicke auf Buttons um Feedback zu sehen
                </div>
            </div>
        );
    }

    return (
        <div className="bg-sheratan-card border border-slate-700 rounded-lg overflow-hidden">
            <div className="px-3 py-2 border-b border-slate-700 flex items-center justify-between">
                <span className="text-xs text-slate-400">Action Log</span>
                <button
                    onClick={clear}
                    className="p-1 text-slate-500 hover:text-slate-300 transition"
                    title="Log leeren"
                >
                    <Trash2 className="w-3 h-3" />
                </button>
            </div>
            <div className="max-h-32 overflow-y-auto">
                {logs.slice().reverse().map((entry) => {
                    const config = levelConfig[entry.level];
                    const Icon = config.icon;
                    return (
                        <div
                            key={entry.id}
                            className="px-3 py-1.5 flex items-start gap-2 text-xs border-b border-slate-800 last:border-0"
                        >
                            <Icon className={`w-3.5 h-3.5 mt-0.5 flex-shrink-0 ${config.color}`} />
                            <div className="flex-1 min-w-0">
                                <span className="text-slate-300">{entry.message}</span>
                            </div>
                            <span className="text-slate-600 flex-shrink-0">
                                {entry.timestamp.toLocaleTimeString('de-DE', { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
                            </span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
