@echo off
REM ============================================
REM Sheratan Production Start Script (Windows)
REM ============================================

echo [SHERATAN] Starting in PRODUCTION mode...
echo.

REM Set Governance to LIVE
set GOV_ENABLED=1
set GOV_DRY_RUN=0
set LEDGER_DEFAULT_MARGIN=0.15
set LEDGER_MAX_MARGIN=0.50

REM Set Writer Mode
set LEDGER_MODE=writer
set LEDGER_JOURNAL_HTTP_PORT=8100

REM Set Paths
set LEDGER_JOURNAL_PATH=ledger_events.jsonl

REM Rate Limiting
set SETTLEMENT_RATE_LIMIT_PER_MIN=100

echo [CONFIG] Governance: ENABLED (LIVE)
echo [CONFIG] Mode: WRITER
echo [CONFIG] HTTP Port: 8100
echo [CONFIG] Default Margin: 15%%
echo.

REM Start Core API
echo [SHERATAN] Starting Core API on port 8001...
start "Sheratan Core" cmd /k "python -m uvicorn core.main:app --host 0.0.0.0 --port 8001 --reload"

timeout /t 3 /nobreak >nul

REM Start Journal Sync API
echo [SHERATAN] Starting Journal Sync API on port 8100...
start "Journal Sync API" cmd /k "python -m mesh.registry.journal_sync_api"

timeout /t 2 /nobreak >nul

echo.
echo ============================================
echo [SHERATAN] System is LIVE in PRODUCTION mode
echo ============================================
echo.
echo WARNING: Settlements are now REAL and will modify balances!
echo.
echo Monitoring commands:
echo - Reconciliation: python -m mesh.registry.reconciliation_report ledger_events.jsonl
echo - Journal verify: python -m core.journal_cli verify ledger_events.jsonl
echo - Worker stats: curl http://localhost:8001/api/mesh/workers
echo.
echo To stop: Close the terminal windows or run STOP_SHERATAN.bat
echo.
pause
