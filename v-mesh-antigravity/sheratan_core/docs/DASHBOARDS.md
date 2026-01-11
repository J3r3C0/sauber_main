# 📊 Sheratan Dashboards - Übersicht

## 🎯 Zentrale Index-Seite

**Datei:** `index.html`  
**Öffnen:**
```
file:///c:/Sheratan/2_sheratan_coreindex.html
```

Diese Seite verlinkt alle verfügbaren Dashboards!

---

## 📌 Verfügbare Dashboards

### 1. **Self-Loop Dashboard** (EMPFOHLEN)
- **URL:** `http://localhost:8001/static/selfloop-dashboard.html`
- **Datei:** `selfloop-dashboard.html`
- **Backend:** Port 8088 (lokal) oder 8000 (Docker)
- **Verwendung:** Kompakte Übersicht für Self-Loop Monitoring

### 2. **Sheratan Dashboard** (Vollständig)
- **URL:** `http://localhost:8001/static/sheratan-dashboard.html`
- **Datei:** `sheratan-dashboard.html`
- **Backend:** Port 8000 (Docker)
- **Verwendung:** Detaillierte Missions/Tasks/Jobs Verwaltung

### 3. **React Dashboard** (Development)
- **URL:** `http://localhost:5174`
- **Ordner:** `react-dashboard/`
- **Backend:** Port 8088 (lokal)
- **Start:** `cd react-dashboard && npm run dev`
- **Verwendung:** Hot-Reload Development

### 4. **Minimal Control Panel**
- **URL:** `http://localhost:8001/static/sheratan-minimal-control.html`
- **Datei:** `core/sheratan_core_v2/sheratan-minimal-control.html`
- **Verwendung:** Grundlegende Steuerung

---

## 🚀 Wie starten?

### **Option A: LOCAL Setup**
```batch
start_local.bat
```
Öffnet automatisch: Self-Loop Dashboard (Port 8088)

### **Option B: DOCKER Setup**
```batch
start_docker.bat
```
Öffnet automatisch: Sheratan Dashboard (Port 8000)

---

## 🔗 Dashboard-Verknüpfungen

### **Über Core-Server (EMPFOHLEN):**
```
http://localhost:8001/static/selfloop-dashboard.html
http://localhost:8001/static/sheratan-dashboard.html
http://localhost:8001/static/sheratan-minimal-control.html
```

### **Direkte Datei-Links:**
```
file:///c:/Sheratan/2_sheratan_coreselfloop-dashboard.html
file:///c:/Sheratan/2_sheratan_coresheratan-dashboard.html
file:///c:/Sheratan/2_sheratan_coreindex.html  (Zentrale Übersicht)
```

**⚠️ Hinweis:** Direkte `file://` Links haben CORS-Probleme! Verwenden Sie den Core-Server (`/static/`).

---

## 📋 Port-Übersicht

| Service | Docker | Local | Dashboard |
|---------|--------|-------|-----------|
| Core | 8001 | - | Alle HTML |
| Backend | 8000 | 8088 | Variiert |
| WebRelay | 3000 | 3000 | - |
| React Dev | - | 5174 | React |

---

## ✅ Empfehlung

**Für tägliche Nutzung:**
1. `start_local.bat` oder `start_docker.bat`
2. Öffnen: `http://localhost:8001/static/selfloop-dashboard.html`

**Für Übersicht:**
1. Öffnen: `file:///c:/Sheratan/2_sheratan_coreindex.html`
2. Dashboard aus der Liste auswählen

---

**Status:** ✅ Alle Dashboards korrekt verknüpft!
