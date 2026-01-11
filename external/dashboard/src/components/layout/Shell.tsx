import { ReactNode } from "react";
import { Sidebar, type SheratanTabId } from "./Sidebar";
import { Topbar } from "./Topbar";

interface ShellProps {
  activeTab: SheratanTabId;
  onTabChange: (id: SheratanTabId) => void;
  children: ReactNode;
}

export function Shell({ activeTab, onTabChange, children }: ShellProps) {
  return (
    <div className="min-h-screen bg-sheratan-bg text-slate-50 flex">
      <Sidebar activeTab={activeTab} onTabChange={onTabChange} />
      <div className="flex-1 flex flex-col min-w-0">
        <Topbar />
        <main className="flex-1 overflow-y-auto px-6 py-4">
          {children}
        </main>
      </div>
    </div>
  );
}
