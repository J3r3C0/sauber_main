@echo off
REM ============================================
REM Sheratan ULTIMATE System (WebRelay Only)
REM No Python Worker File Watching
REM ============================================

echo [SHERATAN] Starting ULTIMATE system (WebRelay Worker Only)...
echo.

REM Set Governance to Dry-Run
set GOV_ENABLED=1
set GOV_DRY_RUN=1
set LEDGER_DEFAULT_MARGIN=0.15
set LEDGER_MAX_MARGIN=0.50

REM Set Writer Mode
set LEDGER_MODE=writer
set LEDGER_JOURNAL_HTTP_PORT=8100

REM Set Paths
set LEDGER_JOURNAL_PATH=ledger_events.jsonl

REM Chrome Debug Settings
set CHROME_PROFILE_PATH=%CD%\data\chrome_profile
set CHROME_DEBUG_PORT=9222

echo [CONFIG] Governance: ENABLED (DRY-RUN)
echo [CONFIG] Mode: WRITER
echo [CONFIG] Chrome Debug Port: %CHROME_DEBUG_PORT%
echo.

REM Ensure directories exist
if not exist "data\webrelay_out" mkdir "data\webrelay_out"
if not exist "data\webrelay_in" mkdir "data\webrelay_in"
if not exist "%CHROME_PROFILE_PATH%" mkdir "%CHROME_PROFILE_PATH%"

REM Start Chrome in Debug Mode
echo [CHROME] Starting Chrome in debug mode...
start "Chrome Debug" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=%CHROME_DEBUG_PORT% --user-data-dir="%CHROME_PROFILE_PATH%" --no-first-run --no-default-browser-check

timeout /t 3 /nobreak >nul

REM Start Core API
echo [SHERATAN] Starting Core API on port 8001...
start "Sheratan Core" cmd /k "python -m uvicorn core.main:app --host 0.0.0.0 --port 8001 --reload"

timeout /t 3 /nobreak >nul

REM Start Journal Sync API
echo [SHERATAN] Starting Journal Sync API on port 8100...
start "Journal Sync API" cmd /k "python -m mesh.registry.journal_sync_api"

timeout /t 2 /nobreak >nul

REM Start WebRelay Worker (ONLY worker watching files)
echo [SHERATAN] Building and starting WebRelay Worker...
cd external\webrelay
start "WebRelay Worker" cmd /k "npm run build && npm start"
cd ..\..

timeout /t 3 /nobreak >nul

echo.
echo ============================================
echo [SHERATAN] ULTIMATE System is LIVE (WebRelay Only)!
echo ============================================
echo.
echo Services running:
echo   1. Chrome Debug (port %CHROME_DEBUG_PORT%)
echo   2. Core API (port 8001)
echo   3. Journal Sync API (port 8100)
echo   4. WebRelay Worker (LLM jobs via Puppeteer)
echo.
echo NOTE: Python Worker is NOT running (no file watching conflict)
echo      WebRelay Worker handles ALL jobs from data/webrelay_out/
echo.
echo Next steps:
echo 1. Send test jobs: python mobile_cli.py launch
echo 2. Watch logs in WebRelay Worker window
echo 3. Check reconciliation: python -m mesh.registry.reconciliation_report ledger_events.jsonl
echo.
echo To stop: run STOP_SHERATAN.bat
echo.
pause
