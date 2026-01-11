# Sheratan Dev Dashboard - Quick Start

## ✅ Phase 1 Setup Complete!

Das Dashboard ist jetzt bereit, echte Daten von den Sheratan APIs zu beziehen.

### Was wurde implementiert:

- ✅ Axios HTTP Client
- ✅ React Query für Data Fetching
- ✅ Environment Variables (.env)
- ✅ API Services (Missions, Jobs, System)
- ✅ React Query Hooks
- ✅ Dependencies installiert

---

## 🚀 Dashboard starten

### 1. Backend starten (Core v2)
```bash
cd c:\Sheratan\2_sheratan_core
python -m core.sheratan_core_v2.main
```
Läuft auf: `http://localhost:8001`

### 2. Frontend starten
```bash
cd c:\Sheratan\1_Sheratan_Dev_Dashbord  
npm run dev
```
Läuft auf: `http://localhost:5173`

---

## 📂 Neue Dateien

### API Layer
- `src/api/client.ts` - Axios Instance
- `src/api/missions.ts` - Missions API
- `src/api/jobs.ts` - Jobs API  
- `src/api/system.ts` - System API

### Hooks
- `src/hooks/useMissions.ts` - Missions Hooks
- `src/hooks/useJobs.ts` - Jobs Hooks

### Config
- `.env` - Environment Variables
- `.env.example` - Template

---

## 🔍 React Query Devtools

Die Devtools sind aktiviert! Im Browser unten links findest du das React Query Icon.
Damit kannst du:
- Cache inspizieren
- Queries manuell refetchen
- Query Status überwachen

---

## ✅ Implementierungsstatus

### Phase 1: Foundation ✅
- Axios + React Query Setup
- Environment Variables
- API Services (Missions, Jobs, System)
- React Query Hooks

### Phase 2: Data Integration ✅  
- MissionsTab mit echten APIs
- Loading/Error States
- Auto-Refresh (5s Missions, 3s Jobs)

### Phase 3: Interactive Features ✅
- Mission erstellen (Modal-Form)
- Job dispatchen
- Job synchronisieren
- Optimistic Updates

### Phase 4: System Monitoring ✅
- Backend-Status-Indikator (Header)
- Live Connection-Check
- Mission Counter

### Nächste Phase: Polish & Optimization
- WebSocket für Echtzeit-Updates
- Erweiterte Fehlerbehandlung
- Performance-Optimierungen

---

**Status**: ✅ **Phasen 1-4 Complete - Voll funktionsfähiges Dashboard mit echten APIs!**