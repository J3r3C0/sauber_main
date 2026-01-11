import { create } from 'zustand';

export type LogLevel = 'info' | 'success' | 'error' | 'warning';

interface LogEntry {
    id: number;
    level: LogLevel;
    message: string;
    timestamp: Date;
}

interface ActionLogStore {
    logs: LogEntry[];
    log: (level: LogLevel, message: string) => void;
    clear: () => void;
}

let logId = 0;

export const useActionLog = create<ActionLogStore>((set) => ({
    logs: [],
    log: (level, message) => {
        const entry: LogEntry = {
            id: ++logId,
            level,
            message,
            timestamp: new Date(),
        };
        set((state) => ({
            logs: [...state.logs.slice(-19), entry], // Keep last 20
        }));
        console.log(`[ActionLog] ${level.toUpperCase()}: ${message}`);
    },
    clear: () => set({ logs: [] }),
}));
