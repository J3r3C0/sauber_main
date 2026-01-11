# 🌐 Sheratan WebRelay Worker

TypeScript WebRelay Worker mit ChatGPT Browser Backend für sheratan-core-poc.

## Quick Start

### 1. Chrome mit Debug-Port starten

```cmd
start_chrome.bat
```

**Wichtig:** Bei ChatGPT einloggen: https://chatgpt.com

### 2. WebRelay starten

```cmd
cd webrelay
start.bat
```

Das Script:
- Installiert Dependencies (`npm install`)
- Baut TypeScript (`npm run build`)
- Startet Worker (`npm start`)

Der Worker überwacht `../webrelay_out/` und schreibt Results nach `../webrelay_in/`.

## Architektur

```
webrelay/
├── src/
│   ├── index.ts              # Main worker loop
│   ├── types.ts              # UnifiedJob/Result types
│   ├── parser.ts             # LCP response parser
│   ├── job-router.ts         # Prompt builder
│   └── backends/
│       └── chatgpt.ts        # Puppeteer browser automation
├── config/
│   └── default-config.json   # Worker configuration  
├── start.bat                 # Windows launcher
└── package.json
```

## Job Format

Kompatibel mit Python worker_loop.py UnifiedJob:

```json
{
  "job_id": "test-001",
  "kind": "agent_plan",
  "created_at": "2025-12-09T12:00:00Z",
  "payload": {
    "task": {
      "kind": "agent_plan",
      "params": {
        "user_prompt": "Analyze the Python files",
        "project_root": "/workspace/project"
      }
    }
  }
}
```

## Result Format

```json
{
  "job_id": "test-001",
  "ok": true,
  "action": "create_followup_jobs",
  "commentary": "Plan created",
  "new_jobs": [...],
  "convoUrl": "https://chatgpt.com/c/xyz",
  "llm_backend": "chatgpt",
  "execution_time_ms": 5230
}
```

## Features

- ✅ ChatGPT Browser Backend via Puppeteer
- ✅ Automatische Prompt-Extraktion aus UnifiedJob
- ✅ LCP Response Parsing
- ✅ create_followup_jobs Format Support
- ✅ Sentinel Detection (`}}}`)
- ✅ Stop-Button Polling
- ✅ Conversation URL Tracking

## Environment

Siehe `.env.example`:

```env
BROWSER_URL=http://127.0.0.1:9222
WEB_INTERFACE_URL=https://chatgpt.com
RELAY_OUT_DIR=webrelay_out
RELAY_IN_DIR=webrelay_in
```

## Testing

```powershell
# Job erstellen
$job = @{
    job_id = "test-001"
    kind = "llm_call"
    created_at = (Get-Date).ToUniversalTime().ToString("o")
    payload = @{
        prompt = "Was ist TypeScript?"
    }
} | ConvertTo-Json

$job | Out-File -Encoding UTF8 ..\webrelay_out\test-001.job.json

# Result prüfen
Get-Content ..\webrelay_in\test-001.result.json | ConvertFrom-Json
```

Fertig! 🚀
