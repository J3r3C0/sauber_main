import { useState } from "react";
import { Plus, X } from "lucide-react";
import { useCreateMission } from "../../hooks/useMissions";

interface CreateMissionFormProps {
    onClose: () => void;
}

export function CreateMissionForm({ onClose }: CreateMissionFormProps) {
    const [title, setTitle] = useState("");
    const [description, setDescription] = useState("");
    const [tags, setTags] = useState("");

    const createMission = useCreateMission();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        const tagsArray = tags
            .split(",")
            .map((t) => t.trim())
            .filter((t) => t.length > 0);

        await createMission.mutateAsync({
            title,
            description,
            tags: tagsArray.length > 0 ? tagsArray : undefined,
        });

        onClose();
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center">
            <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

            <div className="relative w-full max-w-md bg-sheratan-card border border-slate-700 rounded-lg p-6">
                <div className="flex items-center justify-between mb-4">
                    <h2 className="text-lg font-semibold text-slate-100">Neue Mission erstellen</h2>
                    <button
                        onClick={onClose}
                        className="p-1 hover:bg-slate-800 rounded transition"
                    >
                        <X className="w-5 h-5 text-slate-400" />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-1">
                            Titel
                        </label>
                        <input
                            type="text"
                            value={title}
                            onChange={(e) => setTitle(e.target.value)}
                            required
                            className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:border-sheratan-accent"
                            placeholder="z.B. Code-Analyse Projekt X"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-1">
                            Beschreibung
                        </label>
                        <textarea
                            value={description}
                            onChange={(e) => setDescription(e.target.value)}
                            required
                            rows={3}
                            className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:border-sheratan-accent resize-none"
                            placeholder="Was soll diese Mission erreichen?"
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-slate-300 mb-1">
                            Tags (komma-getrennt)
                        </label>
                        <input
                            type="text"
                            value={tags}
                            onChange={(e) => setTags(e.target.value)}
                            className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-slate-100 focus:outline-none focus:border-sheratan-accent"
                            placeholder="z.B. self-loop, analysis, urgent"
                        />
                        <p className="text-xs text-slate-500 mt-1">
                            Optional: Tags mit Komma trennen
                        </p>
                    </div>

                    <div className="flex gap-3 pt-4">
                        <button
                            type="button"
                            onClick={onClose}
                            className="flex-1 px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition"
                        >
                            Abbrechen
                        </button>
                        <button
                            type="submit"
                            disabled={createMission.isPending}
                            className="flex-1 px-4 py-2 bg-sheratan-accent hover:bg-sheratan-accent/80 text-white rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
                        >
                            {createMission.isPending ? "Erstelle..." : "Erstellen"}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
