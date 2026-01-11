import { Bell, X, AlertCircle, AlertTriangle, Info, CheckCircle } from "lucide-react";
import { useState } from "react";
import type { Notification } from "../../types";

interface NotificationCenterProps {
  notifications: Notification[];
  onMarkAsRead: (id: string) => void;
  onClearAll: () => void;
}

export function NotificationCenter({ notifications, onMarkAsRead, onClearAll }: NotificationCenterProps) {
  const [isOpen, setIsOpen] = useState(false);
  const unreadCount = notifications.filter((n) => !n.read).length;

  const getIcon = (type: Notification["type"]) => {
    switch (type) {
      case "error":
        return AlertCircle;
      case "warning":
        return AlertTriangle;
      case "success":
        return CheckCircle;
      default:
        return Info;
    }
  };

  const getColors = (type: Notification["type"]) => {
    switch (type) {
      case "error":
        return "bg-red-500/10 border-red-500/30 text-red-400";
      case "warning":
        return "bg-amber-500/10 border-amber-500/30 text-amber-400";
      case "success":
        return "bg-emerald-500/10 border-emerald-500/30 text-emerald-400";
      default:
        return "bg-sheratan-accent/10 border-sheratan-accent/30 text-sheratan-accent";
    }
  };

  const getCategoryColor = (category: Notification["category"]) => {
    const colors: Record<string, string> = {
      worker: "text-purple-400",
      mesh: "text-sheratan-accent",
      trader: "text-emerald-400",
      selfloop: "text-blue-400",
      api: "text-amber-400",
      mission: "text-pink-400",
    };
    return colors[category] || "text-slate-400";
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="relative p-2 hover:bg-slate-800/50 rounded-lg transition"
      >
        <Bell className="w-5 h-5 text-slate-300" />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 w-5 h-5 bg-sheratan-danger text-white text-xs rounded-full flex items-center justify-center">
            {unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <>
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />
          <div className="absolute right-0 top-12 w-96 bg-sheratan-card border border-slate-700 rounded-lg shadow-2xl z-50 max-h-[600px] flex flex-col">
            <div className="px-4 py-3 border-b border-slate-700 flex items-center justify-between">
              <div>
                <h3 className="text-sm">Notifications</h3>
                <p className="text-xs text-slate-400 mt-0.5">
                  {unreadCount} unread
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={onClearAll}
                  className="text-xs text-slate-400 hover:text-slate-200"
                >
                  Clear all
                </button>
                <button
                  onClick={() => setIsOpen(false)}
                  className="p-1 hover:bg-slate-800 rounded"
                >
                  <X className="w-4 h-4 text-slate-400" />
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-y-auto divide-y divide-slate-800">
              {notifications.length === 0 ? (
                <div className="p-8 text-center text-slate-500 text-sm">
                  No notifications
                </div>
              ) : (
                notifications.map((notification) => {
                  const Icon = getIcon(notification.type);
                  return (
                    <div
                      key={notification.id}
                      className={`p-4 hover:bg-slate-900/40 transition cursor-pointer ${
                        !notification.read ? "bg-slate-900/20" : ""
                      }`}
                      onClick={() => onMarkAsRead(notification.id)}
                    >
                      <div className="flex items-start gap-3">
                        <div className={`p-2 rounded-lg border ${getColors(notification.type)}`}>
                          <Icon className="w-4 h-4" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1">
                            <span className="text-sm text-slate-100">
                              {notification.title}
                            </span>
                            {!notification.read && (
                              <span className="w-2 h-2 bg-sheratan-accent rounded-full" />
                            )}
                          </div>
                          <p className="text-xs text-slate-400 mb-2">
                            {notification.message}
                          </p>
                          <div className="flex items-center gap-2 text-xs">
                            <span className={getCategoryColor(notification.category)}>
                              {notification.category}
                            </span>
                            <span className="text-slate-500">•</span>
                            <span className="text-slate-500">
                              {new Date(notification.timestamp).toLocaleTimeString()}
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}
