@echo off
REM ============================================
REM Sheratan Complete System Start (Phase A Verified)
REM All services including State Machine
REM ============================================

echo [SHERATAN] Starting Complete System...
echo.

REM Ensure directories exist
if not exist "runtime" mkdir "runtime"
if not exist "logs" mkdir "logs"
if not exist "data\webrelay_out" mkdir "data\webrelay_out"
if not exist "data\webrelay_in" mkdir "data\webrelay_in"
if not exist "data\chrome_profile" mkdir "data\chrome_profile"

REM Start Chrome in Debug Mode
echo [1/8] Starting Chrome Debug (port 9222)...
start "Chrome Debug" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%CD%\data\chrome_profile" --no-first-run --no-default-browser-check https://chatgpt.com
timeout /t 3 /nobreak >nul

REM Start Core API (with State Machine)
echo [2/8] Starting Core API (port 8001) with State Machine...
start "Sheratan Core" cmd /k "python -u core\main.py"
timeout /t 5 /nobreak >nul

REM Start Broker
echo [3/8] Starting Broker (port 9000)...
start "Sheratan Broker" cmd /k "python mesh\offgrid\broker\auction_api.py --port 9000"
timeout /t 3 /nobreak >nul

REM Start Host-A
echo [4/8] Starting Host-A (port 8081)...
start "Sheratan Host-A" cmd /k "python mesh\offgrid\host\api_real.py --port 8081 --node_id node-A"
timeout /t 2 /nobreak >nul

REM Start Host-B
echo [5/8] Starting Host-B (port 8082)...
start "Sheratan Host-B" cmd /k "python mesh\offgrid\host\api_real.py --port 8082 --node_id node-B"
timeout /t 2 /nobreak >nul

REM Start WebRelay
echo [6/8] Starting WebRelay (port 3000)...
cd external\webrelay
start "Sheratan WebRelay" cmd /k "npm start"
cd ..\..
timeout /t 5 /nobreak >nul

REM Start Worker
echo [7/8] Starting Worker Loop...
start "Sheratan Worker" cmd /k "python worker\worker_loop.py"
timeout /t 3 /nobreak >nul

REM Start Dashboard
echo [8/8] Starting Dashboard (port 3001)...
cd external\dashboard
start "Sheratan Dashboard" cmd /k "npm run dev"
cd ..\..

echo.
echo ============================================
echo [SHERATAN] Complete System is LIVE!
echo ============================================
echo.
echo Services running:
echo   1. Chrome Debug (port 9222)
echo   2. Core API with State Machine (port 8001)
echo   3. Broker (port 9000)
echo   4. Host-A (port 8081)
echo   5. Host-B (port 8082)
echo   6. WebRelay (port 3000)
echo   7. Worker Loop
echo   8. Dashboard (port 3001)
echo.
echo State Machine Endpoints:
echo   - GET  http://localhost:8001/api/system/state
echo   - POST http://localhost:8001/api/system/state/transition
echo   - GET  http://localhost:8001/api/system/state/history
echo.
echo Dashboard: http://localhost:3001
echo.
echo To stop: run STOP_SHERATAN.bat
echo.
pause
