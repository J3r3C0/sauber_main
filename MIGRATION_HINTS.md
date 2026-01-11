# MIGRATION HINTS: C:\Sheratan\sheratan

Diese Datei dient als Orientierungshilfe für den "Clean Build" Agenten. Sie definiert, welche Teile aus dem alten Repo (`C:\Sheratan\sheratan`) übernommen werden sollen.

## ✅ MUSS MIT (Core Components)

Diese Ordner enthalten die essentielle Logik und müssen in die neue Struktur (`C:\sauber_main`) migriert werden:

1.  **`core/`**
    *   **Inhalt**: FastAPI Kernel, LCP Actions, Storage, Models.
    *   **Ziel**: `mesh/core/` (oder `core/` je nach neuer Struktur).
    *   **Wichtig**: Dies ist das Herzstück der V2 API.

2.  **`worker/`**
    *   **Inhalt**: `worker_loop.py` (Der LCP Worker).
    *   **Ziel**: `mesh/worker/` oder integriert in `mesh/core/`.

3.  **`dashboard/`**
    *   **Inhalt**: Das React Frontend (Vite).
    *   **Ziel**: `dashboard/`.

4.  **`webrelay/`**
    *   **Inhalt**: Der TypeScript/Puppeteer Bridge Server.
    *   **Ziel**: `external/webrelay/`.
    *   **Hinweis**: Lief stabil auf Port 3000.

## ⚠️ BRAUCHBAR (Templates & Tools)

Diese Dateien dienen als Vorlage oder Utilities:

1.  **`RESET_SYSTEM.ps1`** -> Als Vorlage für ein globales Reset-Skript nutzen.
2.  **`START.ps1`** -> Als Vorlage für das Master-Startup-Skript.
3.  **`print_status.py`** & **`check_test.py`** -> Nützliche Debug-Tools, evtl. nach `tools/` verschieben.

## ❌ IGNOPIEREN (Legacy / Transient)

Nicht kopieren! Diese Ordner enthalten Datenreste oder veraltete Skripte:

*   `data/` (Missionen, Logs, Job-Queues -> Wir wollen einen frischen Start)
*   `.chrome-debug/` (Browser Cache)
*   `backup.bat`
*   `verify_truncation.py`
*   `START-ALT.ps1`, `START.bat`
