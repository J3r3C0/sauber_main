@echo off
REM ============================================
REM Sheratan SIMPLE System (No LLM)
REM For File Operations Only
REM ============================================

echo [SHERATAN] Starting SIMPLE system (File Operations Only)...
echo.

REM Set Governance to Dry-Run
set GOV_ENABLED=1
set GOV_DRY_RUN=1
set LEDGER_DEFAULT_MARGIN=0.15

REM Set Writer Mode
set LEDGER_MODE=writer
set LEDGER_JOURNAL_HTTP_PORT=8100

REM Set Paths
set RELAY_OUT_DIR=data\webrelay_out
set RELAY_IN_DIR=data\webrelay_in

REM Ensure directories exist
if not exist "data\webrelay_out" mkdir "data\webrelay_out"
if not exist "data\webrelay_in" mkdir "data\webrelay_in"

echo [CONFIG] Governance: ENABLED (DRY-RUN)
echo [CONFIG] Mode: WRITER (File Operations Only)
echo.

REM Start Core API
echo [SHERATAN] Starting Core API on port 8001...
start "Sheratan Core" cmd /k "python -m uvicorn core.main:app --host 0.0.0.0 --port 8001 --reload"

timeout /t 3 /nobreak >nul

REM Start Journal Sync API
echo [SHERATAN] Starting Journal Sync API on port 8100...
start "Journal Sync API" cmd /k "python -m mesh.registry.journal_sync_api"

timeout /t 2 /nobreak >nul

REM Start Python Worker (File Operations Only)
echo [SHERATAN] Starting Python Worker (File Ops)...
start "Python Worker" cmd /k "python worker\worker_loop.py"

timeout /t 2 /nobreak >nul

echo.
echo ============================================
echo [SHERATAN] SIMPLE System is LIVE
echo ============================================
echo.
echo Services running:
echo   1. Core API (port 8001)
echo   2. Journal Sync API (port 8100)
echo   3. Python Worker (list_files, read_file, write_file)
echo.
echo NOTE: LLM calls (agent_plan) will FAIL - this is expected!
echo      Use this for file operations and testing governance.
echo.
echo To stop: run STOP_SHERATAN.bat
echo.
pause
