import { useState } from 'react';
import { Rocket, Loader2 } from 'lucide-react';
import { selfloopApi } from '../../api/selfloop';

/**
 * Quick Start: Standard Code Analysis Button
 * One-click Self-Loop mission using Backend PoC
 */
export function QuickStartButton() {
    const [isLoading, setIsLoading] = useState(false);
    const [result, setResult] = useState<{ success: boolean; message: string } | null>(null);

    const handleQuickStart = async () => {
        setIsLoading(true);
        setResult(null);

        try {
            const response = await selfloopApi.quickStartCodeAnalysis();
            setResult({
                success: true,
                message: `✅ Mission ${response.mission.id.substring(0, 8)}... gestartet!`,
            });

            // Refresh page after 2 seconds to show new mission
            setTimeout(() => {
                window.location.reload();
            }, 2000);
        } catch (error: any) {
            console.error('Quick Start failed:', error);
            setResult({
                success: false,
                message: `❌ Fehler: ${error?.response?.data?.detail || error.message || 'Backend PoC nicht erreichbar'}`,
            });
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="flex items-center gap-3">
            <button
                onClick={handleQuickStart}
                disabled={isLoading}
                className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 
                           hover:from-emerald-500 hover:to-teal-500 disabled:from-slate-700 disabled:to-slate-700
                           text-white font-medium rounded-lg shadow-lg hover:shadow-emerald-500/25
                           transition-all duration-200"
            >
                {isLoading ? (
                    <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                    <Rocket className="w-4 h-4" />
                )}
                <span>🚀 Quick Start: Code Analysis</span>
            </button>

            {result && (
                <span className={`text-sm ${result.success ? 'text-emerald-400' : 'text-red-400'}`}>
                    {result.message}
                </span>
            )}
        </div>
    );
}
