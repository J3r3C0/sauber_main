# WebRelay Analyse: Docker vs. Lokal

## 🔍 Kernfrage
**Funktioniert WebRelay aus dem Docker-Container oder muss es lokal laufen?**

---

## ✅ Antwort: **Beides kann funktionieren!**

Der Unterschied liegt in der **Chrome-Verbindung** und den **Volume-Pfaden**.

---

## 📊 Vergleich: Docker vs. Lokal

| Aspekt | Docker WebRelay | Lokales WebRelay |
|--------|----------------|------------------|
| **Chrome-Verbindung** | `http://host.docker.internal:9222` | `http://127.0.0.1:9222` |
| **webrelay_out Pfad** | `/app/webrelay_out` (Docker Volume) | `C:\Sheratan\2_sheratan_core\webrelay_out` (Host) |
| **webrelay_in Pfad** | `/app/webrelay_in` (Docker Volume) | `C:\Sheratan\2_sheratan_core\webrelay_in` (Host) |
| **Port** | 3000 (im Container) | 3000 (auf Host) |

---

## ⚠️ Das eigentliche Problem: Volume Mismatch

### Aktueller Zustand:
```
Docker Worker → schreibt in Named Volume "relay-out"
WebRelay (lokal) → schaut auf Host-Ordner "webrelay_out/" → LEER!
```

### Das Problem ist NICHT Docker vs. Lokal!

Das Problem ist, dass der **Docker Worker** in ein **Named Volume** schreibt,
aber das **lokale WebRelay** auf einen **Host-Ordner** schaut.

---

## 🛠️ Lösungsoptionen

### Option A: **Alles in Docker** (empfohlen)
```yaml
# docker-compose.yml - WebRelay aktivieren
webrelay:
  build: ./webrelay
  ports:
    - "3000:3000"
  volumes:
    - relay-out:/app/webrelay_out  # ✅ Gleiches Volume wie Worker
    - relay-in:/app/webrelay_in
```
- Worker und WebRelay teilen Named Volumes
- Chrome muss mit `--remote-debugging-port=9222` laufen
- WebRelay verbindet via `host.docker.internal:9222`

### Option B: **Alles Lokal** (aktueller Workaround)
```yaml
# docker-compose.yml - Worker Volumes ändern
worker:
  volumes:
    - ./webrelay_out:/webrelay_out  # ← Host-Ordner statt Named Volume!
    - ./webrelay_in:/webrelay_in
    - ./project:/workspace/project
```
- Worker schreibt in Host-Ordner
- Lokales WebRelay findet die Dateien
- ⚠️ Erfordert docker-compose.yml Änderung

### Option C: **HTTP API statt File Watcher**
WebRelay hat auch HTTP Endpoints:
- `POST /api/job/submit` - Job direkt senden
- Umgeht das File-System komplett
- Erfordert Code-Änderung im Worker

---

## 📝 Empfehlung

**Option A (Alles in Docker)** ist der sauberste Ansatz:

1. WebRelay im Docker aktivieren (bereits in docker-compose.yml definiert)
2. Chrome auf Host mit Debug-Port starten
3. Lokales WebRelay stoppen

**Oder Option B** wenn du lokal entwickeln willst:

1. docker-compose.yml anpassen (Host-Mounts statt Named Volumes)
2. Docker neu starten
3. Lokales WebRelay läuft weiter

---

## 🔧 Quick Fix für Option B

Ersetze in `docker-compose.yml`:

```yaml
# ALT (Named Volumes):
volumes:
  - relay-out:/webrelay_out
  - relay-in:/webrelay_in

# NEU (Host-Mounts):
volumes:
  - ./webrelay_out:/webrelay_out
  - ./webrelay_in:/webrelay_in
```

Dann: `docker-compose down && docker-compose up -d`

---

## ✅ Job-Typen Klarstellung

Die unterschiedlichen Job-Typen sind **gewollt und getrennt**:

| Job-Typ | Erstellt durch | Worker | Ziel |
|---------|---------------|--------|------|
| **Self-Loop/LCP** | Quick Start, startSelfLoop() | WebRelay → ChatGPT | Autonome Planung |
| **Regular Jobs** | Add Job Modal | Docker Worker → Direct LLM | Einzelne Tasks |

Dies ist **kein Bug**, sondern **by Design** - verschiedene Tools für verschiedene Zwecke.

---

## 📅 Letzte Aktualisierung
2024-12-14 14:50
