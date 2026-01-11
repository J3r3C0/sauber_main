import { useState } from "react";
import { RotateCw, Loader2 } from "lucide-react";
import { useStartSelfLoop } from "../../hooks/useSelfLoop";

interface StartSelfLoopButtonProps {
    missionId: string;
    missionName: string;
    onSuccess?: () => void;
}

export function StartSelfLoopButton({ missionId, missionName, onSuccess }: StartSelfLoopButtonProps) {
    const [showModal, setShowModal] = useState(false);
    const [goal, setGoal] = useState("");
    const { mutate: startSelfLoop, isPending } = useStartSelfLoop();

    const handleStart = () => {
        if (!goal.trim()) return;

        startSelfLoop(
            {
                missionId,
                goal: goal.trim(),
                options: { modelHint: "gpt-4o", temperature: 0.3 }
            },
            {
                onSuccess: () => {
                    setShowModal(false);
                    setGoal("");
                    onSuccess?.();
                },
                onError: (error) => {
                    console.error("Failed to start self-loop:", error);
                    alert("Fehler beim Starten des Self-Loops");
                },
            }
        );
    };

    return (
        <>
            <button
                onClick={() => setShowModal(true)}
                className="flex items-center gap-2 px-4 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-lg transition shadow-lg shadow-emerald-900/30"
            >
                <RotateCw className="w-4 h-4" />
                Start Self-Loop
            </button>

            {/* Modal */}
            {showModal && (
                <div className="fixed inset-0 z-[60] flex items-center justify-center">
                    <div
                        className="absolute inset-0 bg-black/70 backdrop-blur-sm"
                        onClick={() => setShowModal(false)}
                    />
                    <div className="relative bg-sheratan-card border border-emerald-700/50 rounded-xl p-6 w-full max-w-lg shadow-2xl">
                        <h3 className="text-lg font-medium text-emerald-300 mb-4 flex items-center gap-2">
                            <RotateCw className="w-5 h-5" />
                            Self-Loop Starten
                        </h3>

                        <p className="text-sm text-slate-400 mb-4">
                            Startet einen autonomen Self-Loop für Mission: <br />
                            <span className="text-slate-200 font-medium">{missionName}</span>
                        </p>

                        <div className="mb-4">
                            <label className="block text-xs text-slate-400 mb-2">
                                Zielbeschreibung (Goal)
                            </label>
                            <textarea
                                value={goal}
                                onChange={(e) => setGoal(e.target.value)}
                                placeholder="Beschreibe das Ziel, das der Self-Loop erreichen soll..."
                                className="w-full h-24 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-200 placeholder-slate-500 focus:border-emerald-500 focus:outline-none resize-none"
                            />
                        </div>

                        <div className="bg-slate-900/50 border border-slate-800 rounded-lg p-3 mb-4">
                            <p className="text-[11px] text-slate-500">
                                ℹ️ Der Self-Loop führt bis zu 10 Iterationen aus. Jede Iteration analysiert
                                den aktuellen Stand (A), plant den nächsten Schritt (B), setzt ihn um (C)
                                und schlägt den Folge-Loop vor (D).
                            </p>
                        </div>

                        <div className="flex justify-end gap-3">
                            <button
                                onClick={() => setShowModal(false)}
                                className="px-4 py-2 text-sm text-slate-400 hover:text-slate-200 transition"
                            >
                                Abbrechen
                            </button>
                            <button
                                onClick={handleStart}
                                disabled={isPending || !goal.trim()}
                                className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 disabled:bg-slate-700 disabled:text-slate-500 text-white rounded-lg transition text-sm"
                            >
                                {isPending ? (
                                    <>
                                        <Loader2 className="w-4 h-4 animate-spin" />
                                        Startet...
                                    </>
                                ) : (
                                    <>
                                        <RotateCw className="w-4 h-4" />
                                        Loop Starten
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    );
}
