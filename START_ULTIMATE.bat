@echo off
REM ============================================
REM Sheratan ULTIMATE System Start
REM Core + Workers + Chrome Debug Profile
REM ============================================

echo [SHERATAN] Starting ULTIMATE system with Chrome Debug Profile...
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
set RELAY_OUT_DIR=data\webrelay_out
set RELAY_IN_DIR=data\webrelay_in

REM Chrome Debug Settings
set CHROME_PROFILE_PATH=%CD%\data\chrome_profile
set CHROME_DEBUG_PORT=9222

echo [CONFIG] Governance: ENABLED (DRY-RUN)
echo [CONFIG] Mode: WRITER
echo [CONFIG] Chrome Debug Port: %CHROME_DEBUG_PORT%
echo [CONFIG] Chrome Profile: %CHROME_PROFILE_PATH%
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

REM Start Python Worker Loop
echo [SHERATAN] Starting Python Worker Loop...
start "Python Worker" cmd /k "python worker\worker_loop.py"

timeout /t 2 /nobreak >nul

REM Start WebRelay Worker
echo [SHERATAN] Building and starting WebRelay Worker...
cd external\webrelay
start "WebRelay Worker" cmd /k "npm run build && npm start"
cd ..\..

timeout /t 3 /nobreak >nul

echo.
echo ============================================
echo [SHERATAN] ULTIMATE System is LIVE!
echo ============================================
echo.
echo Services running:
echo   1. Chrome Debug (port %CHROME_DEBUG_PORT%, profile: data\chrome_profile)
echo   2. Core API (port 8001)
echo   3. Journal Sync API (port 8100)
echo   4. Python Worker Loop (file operations)
echo   5. WebRelay Worker (LLM calls via Puppeteer)
echo.
echo Chrome is ready for Puppeteer automation!
echo.
echo Next steps:
echo 1. Send test jobs: python mobile_cli.py launch
echo 2. Watch logs in the 5 windows
echo 3. Check reconciliation: python -m mesh.registry.reconciliation_report ledger_events.jsonl
echo.
echo To stop: run STOP_SHERATAN.bat
echo.
pause
