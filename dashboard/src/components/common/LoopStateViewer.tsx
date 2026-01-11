import { RotateCw, TrendingUp, HelpCircle, AlertTriangle, ChevronDown, ChevronUp } from "lucide-react";
import { useState } from "react";
import type { LoopState, SelfLoopParsedSections } from "../../types";

interface LoopStateViewerProps {
    loopState: LoopState;
    latestJobResult?: {
        text?: string;
        output?: string;
        [key: string]: any;
    };
}

export function LoopStateViewer({ loopState, latestJobResult }: LoopStateViewerProps) {
    const [expanded, setExpanded] = useState(true);

    // Try to parse sections from latest job result
    let parsedSections: SelfLoopParsedSections | null = null;
    if (latestJobResult?.text || latestJobResult?.output) {
        const text = latestJobResult.text || latestJobResult.output || "";
        // Simple parsing of A/B/C/D sections
        const aMatch = text.match(/A\)\s*([^\n]+)[\s\S]*?(?=B\)|$)/);
        const bMatch = text.match(/B\)\s*([^\n]+)[\s\S]*?(?=C\)|$)/);
        const cMatch = text.match(/C\)\s*([^\n]+)[\s\S]*?(?=D\)|$)/);
        const dMatch = text.match(/D\)\s*([^\n]+)[\s\S]*?$/);

        if (aMatch || bMatch || cMatch || dMatch) {
            parsedSections = {
                A: aMatch ? aMatch[0] : "",
                B: bMatch ? bMatch[0] : "",
                C: cMatch ? cMatch[0] : "",
                D: dMatch ? dMatch[0] : "",
            };
        }
    }

    const progressPercent = Math.min((loopState.iteration / 10) * 100, 100);

    return (
        <div className="bg-gradient-to-br from-emerald-950/40 to-teal-950/30 border border-emerald-700/50 rounded-lg p-4">
            <div
                className="flex items-center justify-between cursor-pointer"
                onClick={() => setExpanded(!expanded)}
            >
                <div className="flex items-center gap-3">
                    <RotateCw className="w-5 h-5 text-emerald-400" />
                    <div>
                        <h3 className="text-sm font-medium text-emerald-300">Self-Loop Modus</h3>
                        <p className="text-xs text-emerald-400/70">Iteration {loopState.iteration}</p>
                    </div>
                </div>
                <button className="p-1 hover:bg-emerald-900/30 rounded transition">
                    {expanded ? (
                        <ChevronUp className="w-4 h-4 text-emerald-400" />
                    ) : (
                        <ChevronDown className="w-4 h-4 text-emerald-400" />
                    )}
                </button>
            </div>

            {expanded && (
                <div className="mt-4 space-y-3">
                    {/* Iteration Progress */}
                    <div className="bg-slate-950/50 border border-slate-800 rounded p-3">
                        <div className="flex items-center justify-between mb-2">
                            <div className="flex items-center gap-2">
                                <TrendingUp className="w-3.5 h-3.5 text-emerald-400" />
                                <span className="text-xs font-medium text-slate-300">Fortschritt</span>
                            </div>
                            <span className="text-xs text-emerald-400">Iteration {loopState.iteration}</span>
                        </div>
                        <div className="w-full bg-slate-900 rounded-full h-2">
                            <div
                                className="bg-gradient-to-r from-emerald-500 to-teal-500 h-2 rounded-full transition-all duration-500"
                                style={{ width: `${progressPercent}%` }}
                            />
                        </div>
                        <p className="text-[10px] text-slate-500 mt-1">Max. 10 Iterationen</p>
                    </div>

                    {/* History Summary */}
                    {loopState.history_summary && (
                        <div className="bg-slate-950/50 border border-slate-800 rounded p-3">
                            <h4 className="text-xs font-medium text-slate-300 mb-2">📜 Verlauf</h4>
                            <div className="text-[11px] text-slate-400 max-h-32 overflow-auto whitespace-pre-wrap font-mono bg-black/30 rounded p-2">
                                {loopState.history_summary}
                            </div>
                        </div>
                    )}

                    {/* Open Questions */}
                    {loopState.open_questions && loopState.open_questions.length > 0 && (
                        <div className="bg-slate-950/50 border border-slate-800 rounded p-3">
                            <div className="flex items-center gap-2 mb-2">
                                <HelpCircle className="w-3.5 h-3.5 text-amber-400" />
                                <h4 className="text-xs font-medium text-slate-300">Offene Fragen</h4>
                            </div>
                            <ul className="space-y-1">
                                {loopState.open_questions.map((q, idx) => (
                                    <li key={idx} className="text-[11px] text-amber-400 flex items-start gap-2">
                                        <span className="text-amber-600 mt-0.5">•</span>
                                        <span className="flex-1">{q}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Constraints */}
                    {loopState.constraints && loopState.constraints.length > 0 && (
                        <div className="bg-slate-950/50 border border-slate-800 rounded p-3">
                            <div className="flex items-center gap-2 mb-2">
                                <AlertTriangle className="w-3.5 h-3.5 text-red-400" />
                                <h4 className="text-xs font-medium text-slate-300">Einschränkungen</h4>
                            </div>
                            <ul className="space-y-1">
                                {loopState.constraints.map((c, idx) => (
                                    <li key={idx} className="text-[11px] text-red-400 flex items-start gap-2">
                                        <span className="text-red-600 mt-0.5">•</span>
                                        <span className="flex-1">{c}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {/* Latest Iteration Sections (A/B/C/D) */}
                    {parsedSections && (
                        <div className="bg-slate-950/50 border border-slate-800 rounded p-3">
                            <h4 className="text-xs font-medium text-slate-300 mb-2">📋 Letzte Iteration</h4>
                            <div className="space-y-2 text-[11px]">
                                {parsedSections.A && (
                                    <div>
                                        <span className="font-semibold text-sky-400">A) Standortanalyse:</span>
                                        <p className="text-slate-400 ml-4 mt-1 whitespace-pre-wrap">
                                            {parsedSections.A.replace(/^A\)\s*[^\n]*\n/, "")}
                                        </p>
                                    </div>
                                )}
                                {parsedSections.B && (
                                    <div>
                                        <span className="font-semibold text-sky-400">B) Nächster Schritt:</span>
                                        <p className="text-slate-400 ml-4 mt-1 whitespace-pre-wrap">
                                            {parsedSections.B.replace(/^B\)\s*[^\n]*\n/, "")}
                                        </p>
                                    </div>
                                )}
                                {parsedSections.C && (
                                    <div>
                                        <span className="font-semibold text-sky-400">C) Umsetzung:</span>
                                        <p className="text-slate-400 ml-4 mt-1 whitespace-pre-wrap max-h-24 overflow-auto">
                                            {parsedSections.C.replace(/^C\)\s*[^\n]*\n/, "")}
                                        </p>
                                    </div>
                                )}
                                {parsedSections.D && (
                                    <div>
                                        <span className="font-semibold text-emerald-400">D) Nächster Loop:</span>
                                        <p className="text-slate-400 ml-4 mt-1 whitespace-pre-wrap">
                                            {parsedSections.D.replace(/^D\)\s*[^\n]*\n/, "")}
                                        </p>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
}
