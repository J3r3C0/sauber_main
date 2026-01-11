# 🚀 Quick Start - Autonomen Loop testen

## Voraussetzung: Docker Desktop starten

⚠️ **Docker Desktop ist aktuell nicht gestartet.**

Bitte starte Docker Desktop, bevor du fortfährst.

---

## Test-Anleitung

### 1️⃣ System starten

```bash
cd c:\Sheratan\2_sheratan_core
docker-compose up --build
```

**Erwartete Ausgabe:**
```
✓ core        Started
✓ worker      Started  
✓ backend     Started
✓ frontend    Started
✓ webrelay    Started
```

---

### 2️⃣ Dashboard öffnen

Browser öffnen und navigieren zu:
```
http://localhost:8001/control-dashboard.html
```

Falls Port 8001 nicht erreichbar:
- Core läuft auf Port **8001**
- Alternativ kannst du auch direkt die Datei öffnen:
  ```
  file:///c:/Sheratan/2_sheratan_corecontrol-dashboard.html
  ```
  Und manuell auf `http://localhost:8001` konfigurieren

---

### 3️⃣ Test-Prompt eingeben

Im Dashboard in die Textarea eingeben:

```
Analyze Python files in /workspace/project
```

Dann auf **"Send to WebRelay"** klicken.

---

### 4️⃣ Erwartetes Verhalten

**Dashboard:**
1. Zeigt "⏳ Creating mission and calling LLM..." an
2. Wartet ~30 Sekunden
3. Zeigt Response mit Follow-up Jobs:
   ```
   ✅ Response Received
   
   Action: create_followup_jobs
   Commentary: First list all Python files, then read main.py...
   Followup Jobs: 2
   
   Jobs created:
     1. [✓ auto] List Python files (list_files)
        Params: {"root": "/workspace/project", "patterns": ["**/*.py"]}
     2. [○ manual] Read main.py (read_file)
        Params: {"root": "/workspace/project", "rel_path": "main.py"}
   ```

**Was im Hintergrund passiert:**
1. Dashboard erstellt Mission
2. Erstellt Task mit `kind: "agent_plan"`
3. Erstellt & dispatched Job
4. Worker empfängt Job → ruft LLM auf
5. LLM gibt LCP-konformes JSON zurück
6. Worker validiert & schreibt Result
7. Core sync'd Result
8. Dashboard zeigt Result an

**🎯 Wenn Auto-Dispatch funktioniert:**
- Follow-up Job "List Python files" wird automatisch ausgeführt
- Du kannst weitere Follow-up Results sehen

---

### 5️⃣ Logs überprüfen

In einem zweiten Terminal:

```bash
cd c:\Sheratan\2_sheratan_core
docker-compose logs -f worker core
```

**Erwartete Log-Patterns:**

**Worker:**
```
[worker] Processing job file ... (job_id=...)
[worker] handle_job job_id=... task_kind=agent_plan
[worker] Calling LLM at http://...
[worker] ✓ Valid LCP response: action=create_followup_jobs, jobs=2
[worker] Wrote result file ...
```

**Core (wenn LCP Interpreter aktiv):**
```
[lcp_actions] Task 'list_files' not found in mission, creating it...
[lcp_actions] Created task: ... (kind=list_files)
📝 Followup job created and queued: ... (kind=list_files, name=List Python files)
```

---

## ⚠️ Troubleshooting

### Problem: LLM gibt falsches Format

**Symptom:**
```
[worker] ERROR: Job ... missing required 'kind' field (use 'kind', not 'task')
```

**Ursache:** LLM ignoriert Prompt-Anweisungen

**Lösung:**
- Prüfe `SHERATAN_LLM_BASE_URL` in `.env`
- Teste mit strikterem Modell (z.B. GPT-4 statt GPT-3.5)
- Aktiviere `response_format: {type: "json_object"}` (nur OpenAI)

### Problem: Keine Follow-up Jobs werden erstellt

**Symptom:** Dashboard zeigt Response, aber keine Jobs in Logs

**Ursache:** `auto_dispatch: false` oder Backend-Issue

**Lösung:**
1. Prüfe ob `apply_agent_plan` aufgerufen wurde
2. Manuell dispatchen über API:
   ```bash
   curl -X POST http://localhost:8001/api/jobs/{job_id}/dispatch
   ```

### Problem: Docker Compose startet nicht

**Symptom:** Service-Fehler beim Start

**Lösung:**
```bash
# Services neu bauen
docker-compose down
docker-compose build --no-cache
docker-compose up
```

---

## ✅ Erfolgs-Kriterien

Der autonome Loop ist **erfolgreich repariert**, wenn:

1. ✅ Dashboard erstellt Mission ohne Fehler
2. ✅ Worker empfängt Job und ruft LLM auf
3. ✅ LLM gibt valides LCP JSON zurück (`kind`, `name`, `params`)
4. ✅ Worker validiert erfolgreich (Log: `✓ Valid LCP response`)
5. ✅ Core erstellt Follow-up Tasks & Jobs
6. ✅ Follow-up Jobs mit `auto_dispatch: true` werden automatisch ausgeführt
7. ✅ Logs zeigen `📝 Followup job created and queued`

---

## 📊 Nächste Optimierungen (Optional)

Nach erfolgreichem Test:

1. **JSON Schema Validation** hinzufügen für noch strengere Format-Prüfung
2. **Monitoring Metriken** für Follow-up Job Erfolgsrate
3. **Doppelte Follow-up Logik** konsolidieren (Core vs Backend)
4. **Rate Limiting** für LLM Calls implementieren
5. **Retry Logic** für fehlgeschlagene Jobs

---

## 🎉 Viel Erfolg beim Testen!

Der Loop sollte jetzt sauber funktionieren 🚀
