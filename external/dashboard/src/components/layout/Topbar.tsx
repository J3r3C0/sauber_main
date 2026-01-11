import { useState } from "react";
import { NotificationCenter } from "../common/NotificationCenter";
import { SystemStatusBar } from "./SystemStatusBar";
import { mockNotifications } from "../../data/mockData";
import { useLiveSystemStatus } from "../../hooks/useLiveStatus";

export function Topbar() {
  const [notifications, setNotifications] = useState(mockNotifications);
  const { data: liveStatus } = useLiveSystemStatus();

  const handleMarkAsRead = (id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, read: true } : n))
    );
  };

  const handleClearAll = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  // Default status while loading
  const status = liveStatus || {
    selfloopState: 'stopped' as const,
    activeModel: 'loading...',
    meshNodesOnline: 0,
    meshNodesTotal: 0,
    jobsInQueue: 0,
    unreadAlerts: 0,
  };

  return (
    <div>
      <SystemStatusBar status={status} />
      <header className="h-12 border-b border-slate-800 flex items-center justify-between px-6 bg-gradient-to-r from-black/40 via-transparent to-black/20">
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-500">
            sheratan-core · <span className="text-slate-400">localhost</span>
          </span>
        </div>
        <div className="flex items-center gap-2">
          <NotificationCenter
            notifications={notifications}
            onMarkAsRead={handleMarkAsRead}
            onClearAll={handleClearAll}
          />
        </div>
      </header>
    </div>
  );
}

