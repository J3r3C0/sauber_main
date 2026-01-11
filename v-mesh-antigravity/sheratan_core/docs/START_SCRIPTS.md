# 🚀 Sheratan Starter Scripts

## Quick Start Übersicht

### ⭐ Option 1: Ein-Klick-Start (EMPFOHLEN!)
```batch
start_all.bat
```
**Einfach doppelklicken!** Startet automatisch:
- ✅ Chrome im Debug-Modus
- ✅ Docker (Core + Backend + Worker)
- ✅ WebRelay (Port 3000)
- ✅ Dashboard (Browser öffnet automatisch)

**👉 Perfekt für:** Tägliche Nutzung, schneller Start!

---

### Option 2: PowerShell mit React Dashboard
```powershell
.\start_all.ps1
```
**Startet:**
- ✅ Docker (Core + Backend + Worker)
- ✅ Backend Service (Port 8088)
- ✅ WebRelay (Port 3000)
- ✅ React Dashboard (Port 5174)

**👉 Perfekt für:** React Development

---

### Option 2: Schrittweise (Empfohlen für Production)

#### Schritt 1: Chrome im Debug-Modus
```batch
start_chrome.bat
```
- Öffnet Chrome mit Remote Debugging (Port 9222)
- **Wichtig:** Bei ChatGPT einloggen!

#### Schritt 2: Core-System
```batch
start_core.bat
```
Startet via Docker Compose:
- Core (Port 8001)
- Backend (Port 8000)  
- Worker (Background)

#### Schritt 3: WebRelay
```batch
start_webrelay.bat
```
- Startet WebRelay Service (Port 3000)
- Verbindet Core mit ChatGPT

#### Schritt 4: Dashboard öffnen
```batch
start_dashboard.bat
```
- Öffnet: `http://localhost:8001/selfloop-dashboard.html`

---

## 📋 Services Übersicht

| Service | Port | URL | Skript |
|---------|------|-----|--------|
| **Core API** | 8001 | http://localhost:8001 | `start_core.bat` |
| **Backend** | 8000/8088 | http://localhost:8088 | `start_core.bat` |
| **WebRelay** | 3000 | http://localhost:3000 | `start_webrelay.bat` |
| **Self-Loop Dashboard** | 8001 | http://localhost:8001/selfloop-dashboard.html | `start_dashboard.bat` |
| **React Dashboard** | 5174 | http://localhost:5174 | `start_all.ps1` |
| **Chrome Debug** | 9222 | - | `start_chrome.bat` |

---

## 🎯 Empfohlener Workflow

### Für normale Nutzung (HTML Dashboard):
```batch
1. start_chrome.bat      # Chrome starten & bei ChatGPT einloggen
2. start_core.bat        # Core-System (Docker)
3. start_webrelay.bat    # WebRelay Service
4. start_dashboard.bat   # Dashboard öffnen
```

### Für React Development:
```powershell
.\start_all.ps1          # Alles auf einmal
```

---

## 🛑 System stoppen

```batch
docker-compose down      # Docker Container stoppen
```

Dann Ctrl+C in den WebRelay/Backend PowerShell-Fenstern drücken.

---

## 📝 Troubleshooting

### Core startet nicht?
- Docker Desktop läuft?
- Ports 8000/8001 frei?
- `docker-compose logs core`

### WebRelay verbindet nicht?
- Chrome läuft mit `--remote-debugging-port=9222`?
- Bei ChatGPT eingeloggt?
- `curl http://localhost:9222/json/version`

### Dashboard zeigt "Offline"?
- Core läuft? → `curl http://localhost:8001/api/status`
- WebRelay läuft? → `curl http://localhost:3000/health`

---

## 🔧 Logs anschauen

```batch
# Docker Services
docker-compose logs -f core
docker-compose logs -f backend
docker-compose logs -f worker

# WebRelay (im PowerShell-Fenster sichtbar)
# Backend (im PowerShell-Fenster sichtbar)
```
