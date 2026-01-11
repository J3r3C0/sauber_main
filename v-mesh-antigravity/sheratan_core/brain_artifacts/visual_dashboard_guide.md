# Visual Workflow Dashboard - Quick Start Guide

## 🎯 What is it?

An **interactive 3D visualization** of Sheratan Core's runtime architecture, showing the mesh topology and weighted connections between system modules.

![Main Dashboard](file:///C:/Users/jerre/.gemini/antigravity/brain/81c8f671-5d5f-4e87-8f28-bd7f08be8120/main_dashboard_view_1767494432064.png)

---

## 🚀 Quick Start

### Installation

```bash
cd "c:\Projects\2_sheratan_core\dashboards\Visual Workflow Diagram"
npm install
```

### Running

```bash
npm run dev
```

Dashboard opens at: **http://localhost:3000**

---

## 🎨 Features

### 1. **Interactive 3D Visualization**
- **Drag** to rotate the view
- **Click modules** for detailed information
- **Zoom** with mouse wheel

### 2. **View Perspectives**
- **Front View** - Standard perspective
- **Top View** - Birds-eye view (mesh topology)

![Top View](file:///C:/Users/jerre/.gemini/antigravity/brain/81c8f671-5d5f-4e87-8f28-bd7f08be8120/top_view_architecture_1767494561653.png)

### 3. **Module Details**
Click any module to see:
- Internal Components (technologies used)
- Key Files (source code references)
- Workflow Steps (operations performed)
- Connections (integration points)

![Worker Pool Details](file:///C:/Users/jerre/.gemini/antigravity/brain/81c8f671-5d5f-4e87-8f28-bd7f08be8120/worker_pool_details_1767494472654.png)

---

## 📦 System Modules

### 1. **WebRelay / API Gateway**
- Entry point for HTTPS/Broker traffic
- Technologies: Traefik, FastAPI
- Files: `traefik.yml`, `webrelay_bridge.py`

![WebRelay Details](file:///C:/Users/jerre/.gemini/antigravity/brain/81c8f671-5d5f-4e87-8f28-bd7f08be8120/webrelay_details_1767494494708.png)

### 2. **Core Orchestrator**
- Central hub for backend orchestration
- Handles mission/task/job lifecycle
- Files: `main.py`, `lcp_actions.py`

### 3. **Worker Pool**
- Job execution and lease management
- Agent pipeline execution
- Files: `worker.py`, `ai_assistent_codder.py`

### 4. **Unified Event Store**
- Persistent state management
- SQLite + content-addressed chunks
- Files: `storage.py`, `event_types.py`

![Event Store Details](file:///C:/Users/jerre/.gemini/antigravity/brain/81c8f671-5d5f-4e87-8f28-bd7f08be8120/unified_event_store_details_1767494518849.png)

### 5. **Message Bus**
- Async communication queue
- Inter-module messaging
- Files: `message_bus.py`

### 6. **Observability & Security**
- Metrics and monitoring
- Technologies: Prometheus, Grafana
- Files: `prometheus.yml`, `grafana.yml`

### 7. **Memory & LLM Backends**
- Shared state and AI integrations
- External LLM connections
- Files: `memory.py`, `llm_client.py`

---

## 🔗 Mesh Topology

**Connections shown as:**
- **Solid lines** - Direct connections
- **Dashed lines** - Weighted/mesh connections
- **Color coding** - Connection strength

The mesh topology visualizes how modules communicate and depend on each other in a multi-dimensional architecture.

---

## 🎮 Navigation

### Mouse Controls
- **Left Click + Drag** - Rotate view
- **Right Click + Drag** - Pan view
- **Scroll Wheel** - Zoom in/out
- **Click Module** - Show details

### Keyboard Shortcuts
- **R** - Reset view
- **F** - Front view
- **T** - Top view
- **ESC** - Close detail panel

---

## 💡 Use Cases

### For Developers
- Understand system architecture
- Find source files quickly
- Trace data flow
- Debug integration issues

### For Monitoring
- Real-time system overview
- Component health status
- Connection topology
- Performance bottlenecks

### For Documentation
- Visual architecture diagrams
- Component relationships
- Technology stack overview
- Onboarding new team members

---

## 🛠️ Technology Stack

- **Frontend:** React 18 + Vite
- **UI Components:** Radix UI
- **3D Rendering:** Three.js (implied)
- **Styling:** Tailwind CSS
- **Build Tool:** Vite 6.3.5

---

## 📝 Tips

1. **Start with Top View** to see the full mesh topology
2. **Click modules** to understand their role
3. **Follow connections** to trace data flow
4. **Use Reset View** if you get lost
5. **Explore all modules** for complete understanding

---

## 🔧 Customization

The dashboard is built with React components, making it easy to:
- Add new modules
- Customize colors and styles
- Add real-time data
- Integrate with monitoring APIs

Source code: `dashboards/Visual Workflow Diagram/src/`

---

## 🎉 Summary

The Visual Workflow Dashboard provides a **professional, interactive way** to understand and monitor Sheratan Core's architecture. It bridges the gap between code-level implementation and system-level design.

**Perfect for:**
- System understanding
- Architecture documentation
- Real-time monitoring
- Team collaboration
