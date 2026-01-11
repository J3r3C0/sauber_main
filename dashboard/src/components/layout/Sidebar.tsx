import {
  Target,
  Network,
  LineChart,
  MessageSquare,
  FolderTree,
  Activity,
  Terminal,
  Settings,
  Cpu,
  GitBranch,
} from "lucide-react";
import { ActionLog } from "../common/ActionLog";
import sheratanLogo from "../../assets/sheratan-logo.jpg";

export type SheratanTabId =
  | "missions"
  | "mesh"
  | "trader"
  | "chat"
  | "projects"
  | "health"
  | "logs"
  | "settings"
  | "model"
  | "dependencies";

const tabs: {
  id: SheratanTabId;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
}[] = [
    { id: "missions", label: "Missions", icon: Target },
    { id: "mesh", label: "Mesh", icon: Network },
    { id: "trader", label: "Trader", icon: LineChart },
    { id: "chat", label: "Prompt/Chat", icon: MessageSquare },
    { id: "projects", label: "Projects", icon: FolderTree },
    { id: "health", label: "Status/Health", icon: Activity },
    { id: "logs", label: "Live Logs", icon: Terminal },
    { id: "model", label: "Model Inspector", icon: Cpu },
    { id: "dependencies", label: "Dependencies", icon: GitBranch },
    { id: "settings", label: "Settings", icon: Settings },
  ];

interface SidebarProps {
  activeTab: SheratanTabId;
  onTabChange: (id: SheratanTabId) => void;
}

export function Sidebar({ activeTab, onTabChange }: SidebarProps) {
  return (
    <aside className="w-64 bg-black/60 border-r border-slate-800 flex flex-col">
      <div className="h-16 px-4 flex items-center border-b border-slate-800">
        <img
          src={sheratanLogo}
          alt="Sheratan"
          className="h-8 w-8 rounded-lg object-cover mr-2"
        />
        <div>
          <div className="text-sm">Sheratan Dev Core</div>
          <div className="text-[11px] text-slate-400">Mesh · Trader · Selfloop</div>
        </div>
      </div>

      <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto">
        {tabs.map(({ id, label, icon: Icon }) => {
          const active = id === activeTab;
          return (
            <button
              key={id}
              onClick={() => onTabChange(id)}
              className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition
              ${active
                  ? "bg-sheratan-accent/10 text-sheratan-accent border border-sheratan-accent/40"
                  : "text-slate-300 hover:bg-slate-900/70"
                }`}
            >
              <Icon className="w-4 h-4" />
              <span>{label}</span>
            </button>
          );
        })}
      </nav>

      {/* Action Log Widget */}
      <div className="p-2 border-t border-slate-800">
        <ActionLog />
      </div>

      <div className="p-4 border-t border-slate-800">
        <div className="text-[11px] text-slate-500 space-y-1">
          <div>Build: <span className="text-slate-400">v0.4.2-dev</span></div>
          <div>Node: <span className="text-slate-400">sheratan-core</span></div>
        </div>
      </div>
    </aside>
  );
}
