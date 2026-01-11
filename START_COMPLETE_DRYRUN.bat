@echo off
REM ============================================
REM Sheratan COMPLETE System Start (Dry-Run)
REM ============================================

echo [SHERATAN] Starting COMPLETE system in DRY-RUN mode...
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

REM Rate Limiting
set SETTLEMENT_RATE_LIMIT_PER_MIN=50

echo [CONFIG] Governance: ENABLED (DRY-RUN)
echo [CONFIG] Mode: WRITER
echo [CONFIG] HTTP Port: 8100
echo [CONFIG] Default Margin: 15%%
echo.

REM Ensure directories exist
if not exist "data\webrelay_out" mkdir "data\webrelay_out"
if not exist "data\webrelay_in" mkdir "data\webrelay_in"

REM Start Core API
echo [SHERATAN] Starting Core API on port 8001...
start "Sheratan Core" cmd /k "python -m uvicorn core.main:app --host 0.0.0.0 --port 8001 --reload"

timeout /t 3 /nobreak >nul

REM Start Journal Sync API
echo [SHERATAN] Starting Journal Sync API on port 8100...
start "Journal Sync API" cmd /k "python -m mesh.registry.journal_sync_api"

timeout /t 2 /nobreak >nul

REM Start Worker Loop
echo [SHERATAN] Starting Worker Loop...
start "Sheratan Worker" cmd /k "python worker\worker_loop.py"

timeout /t 2 /nobreak >nul

echo.
echo ============================================
echo [SHERATAN] COMPLETE System is LIVE (DRY-RUN)
echo ============================================
echo.
echo Services running:
echo   1. Core API (port 8001)
echo   2. Journal Sync API (port 8100)
echo   3. Worker Loop (monitoring data/webrelay_out/)
echo.
echo Next steps:
echo 1. Send test jobs: python mobile_cli.py launch
echo 2. Watch logs in the 3 terminal windows
echo 3. Check reconciliation: python -m mesh.registry.reconciliation_report ledger_events.jsonl
echo.
echo To stop: run STOP_SHERATAN.bat
echo.
pause
