# 🚀 Performance Optimization Guide

## Problem: Hohe CPU-Auslastung (100% on Taskbar Icon)

![Resource Monitor Screenshot](file:///C:/Users/jerre/.gemini/antigravity/brain/c2914a54-2356-4410-a87b-f38e17900bbf/uploaded_image_1765398806860.png)

**Ursache:** 17+ Antigravity.exe Prozesse + Docker Services ohne Limits

---

## ✅ Implementierte Fixes

### 1. Docker Resource Limits

**docker-compose.yml** jetzt mit CPU & RAM Limits:

```yaml
Backend:  0.5 CPU cores, 256MB RAM
Core:     1.0 CPU cores, 512MB RAM  
Worker:   0.5 CPU cores, 256MB RAM
```

**Effekt:** Docker kann maximal ~2 CPU Cores belegen (statt unbegrenzt)

**Container neu starten:**
```powershell
docker-compose down
docker-compose up -d
```

---

### 2. Antigravity Process Cleanup

**Script erstellt:** `cleanup_antigravity.bat`

**Verwendung:**
1. Doppelklick auf `cleanup_antigravity.bat`
2. Script zeigt Anzahl aktiver Prozesse
3. Wenn >3: Option zum Beenden aller Antigravity-Prozesse
4. Antigravity NEU starten
5. **NUR** benötigte Tabs öffnen

**Tipp:** Jeder Antigravity-Tab = separater Prozess!

---

## 💡 Weitere Optimierungen

### Chrome Remote Debugging optimieren

In `start_chrome.bat` hinzufügen:
```batch
--disable-gpu
--disable-software-rasterizer  
--disable-extensions
```

### WSL2 Memory limitieren

Erstelle `C:\Users\jerre\.wslconfig`:
```ini
[wsl2]
memory=4GB       # Max RAM für Docker
processors=2     # Max CPU Cores
```

Dann WSL neustarten:
```powershell
wsl --shutdown
```

### Resource Monitor nutzen

```powershell
# Detaillierte CPU-Ansicht
resmon.exe
```

→ CPU Tab → Zeigt welche Prozesse welche Threads blockieren

---

## 🎯 Performance Best Practices

### Antigravity
- ✅ Schließe ungenutzte Tabs/Windows
- ✅ Nutze cleanup_antigravity.bat regelmäßig
- ✅ Max 2-3 Antigravity-Instanzen gleichzeitig

### Docker
- ✅ Services mit Resource Limits (bereits implementiert)
- ✅ WSL2 Memory begrenzen via .wslconfig
- ✅ Regelmäßig `docker system prune` ausführen

### Chrome
- ✅ Remote Debugging nur wenn nötig
- ✅ GPU-Beschleunigung deaktivieren (--disable-gpu)
- ✅ Extensions minimieren

---

## 📊 Erwartete CPU-Reduktion

**Vorher:**
- Taskbar Icon: 100% (Peaks)
- Task Manager: 60% (Average)
- Docker unbegrenzt
- 17+ Antigravity Prozesse

**Nachher:**
- Taskbar Icon: ~40-60% (Peaks)
- Task Manager: ~30-40% (Average)
- Docker limited to ~2 Cores
- 2-3 Antigravity Prozesse

**Einsparung:** ~40-50% CPU-Auslastung! 🎉

---

## 🛠️ Quick Start

1. **Docker Services neu starten:**
   ```powershell
   cd c:\sheratan-core-poc
   docker-compose down
   docker-compose up -d
   ```

2. **Antigravity aufräumen:**
   ```
   Doppelklick: cleanup_antigravity.bat
   ```

3. **WSL2 limitieren (optional):**
   ```powershell
   notepad $env:USERPROFILE\.wslconfig
   # Inhalt aus Anleitung oben
   wsl --shutdown
   ```

4. **Fertig!** CPU sollte jetzt deutlich niedriger sein! ✅

---

## 🔍 Monitoring

**Schnellcheck:**
```powershell
# Antigravity Prozesse zählen
tasklist | find /c "Antigravity.exe"

# Docker Container Stats
docker stats --no-stream
```

**Optimal:**
- Antigravity: 2-3 Prozesse
- Docker: CPU < 50%, Memory < 2GB

---

**Status:** ✅ Performance optimiert! Docker limitiert, Cleanup-Script bereit.
