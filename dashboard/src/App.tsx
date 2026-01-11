import { useState } from "react";
import { Shell } from "./components/layout/Shell";
import { MissionsTab } from "./features/missions/MissionsTab";
import { MeshTab } from "./features/mesh/MeshTab";
import { TraderTab } from "./features/trader/TraderTab";
import { ChatTab } from "./features/chat/ChatTab";
import { ProjectsTab } from "./features/projects/ProjectsTab";
import { HealthTab } from "./features/health/HealthTab";
import { LogsTab } from "./features/logs/LogsTab";
import { SettingsTab } from "./features/settings/SettingsTab";
import { ModelInspectorTab } from "./features/model/ModelInspectorTab";
import { DependencyMapTab } from "./features/dependencies/DependencyMapTab";
import type { SheratanTabId } from "./components/layout/Sidebar";

function App() {
  const [activeTab, setActiveTab] = useState<SheratanTabId>("missions");

  return (
    <Shell activeTab={activeTab} onTabChange={setActiveTab}>
      {activeTab === "missions" && <MissionsTab />}
      {activeTab === "mesh" && <MeshTab />}
      {activeTab === "trader" && <TraderTab />}
      {activeTab === "chat" && <ChatTab />}
      {activeTab === "projects" && <ProjectsTab />}
      {activeTab === "health" && <HealthTab />}
      {activeTab === "logs" && <LogsTab />}
      {activeTab === "model" && <ModelInspectorTab />}
      {activeTab === "dependencies" && <DependencyMapTab />}
      {activeTab === "settings" && <SettingsTab />}
    </Shell>
  );
}

export default App;
