@echo off
REM ============================================
REM Sheratan Worker Start Script (Windows)
REM ============================================

echo [WORKER] Starting Sheratan Worker Loop...
echo.

REM Set Worker Environment
set RELAY_OUT_DIR=data\webrelay_out
set RELAY_IN_DIR=data\webrelay_in

echo [CONFIG] Monitoring: %RELAY_OUT_DIR%
echo [CONFIG] Results to: %RELAY_IN_DIR%
echo.

REM Ensure directories exist
if not exist "data\webrelay_out" mkdir "data\webrelay_out"
if not exist "data\webrelay_in" mkdir "data\webrelay_in"

REM Start Worker Loop
echo [WORKER] Starting worker loop...
start "Sheratan Worker" cmd /k "python worker\worker_loop.py"

timeout /t 2 /nobreak >nul

echo.
echo ============================================
echo [WORKER] Worker is ACTIVE
echo ============================================
echo.
echo Worker is now monitoring: data\webrelay_out\
echo Jobs will be processed and results written to: data\webrelay_in\
echo.
echo To stop: Close the "Sheratan Worker" window or run STOP_SHERATAN.bat
echo.
pause
