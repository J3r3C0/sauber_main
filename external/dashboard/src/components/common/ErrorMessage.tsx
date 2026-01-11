import { AlertCircle } from "lucide-react";

interface ErrorMessageProps {
    error: Error | unknown;
    title?: string;
}

export function ErrorMessage({ error, title = "Fehler beim Laden" }: ErrorMessageProps) {
    const errorMessage = error instanceof Error ? error.message : "Ein unbekannter Fehler ist aufgetreten";

    return (
        <div className="bg-red-500/10 border border-red-500/50 rounded-lg p-4">
            <div className="flex items-center gap-2 mb-2">
                <AlertCircle className="w-5 h-5 text-red-400" />
                <h3 className="text-red-400 font-semibold">{title}</h3>
            </div>
            <p className="text-sm text-red-300">{errorMessage}</p>
            <p className="text-xs text-red-400/70 mt-2">
                Stelle sicher, dass das Backend läuft (Port 8001)
            </p>
        </div>
    );
}
