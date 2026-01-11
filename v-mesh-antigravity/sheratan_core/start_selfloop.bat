@echo off
echo.
echo ====================================================
echo   Sheratan Self-Loop System - Complete Startup
echo ====================================================
echo.
echo This script will:
echo  1. Start Chrome in Debug Mode (Port 9222)
echo  2. Start Docker services (Core, Backend, Worker, WebRelay)
echo  3. Open Self-Loop Dashboard
echo  4. Open Sheratan Control Dashboard
echo.

REM Check if Docker is running
docker ps >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Docker is not running!
    echo Please start Docker Desktop first.
    echo.
    pause
    exit /b 1
)

echo ====================================
echo   [1/4] Starting Chrome Debug Mode
echo ====================================
echo.

REM Kill existing Chrome instances on port 9222
for /f "tokens=5" %%a in ('netstat -aon ^| find ":9222" ^| find "LISTENING"') do taskkill /F /PID %%a >nul 2>&1

REM Start Chrome in debug mode
start chrome --remote-debugging-port=9222 ^
    --remote-debugging-address=0.0.0.0 ^
    --remote-allow-origins=* ^
    --user-data-dir="%TEMP%\chrome-sheratan-selfloop" ^
    --new-window https://chatgpt.com

echo Chrome started on port 9222
echo Please log in to ChatGPT in the opened window
echo.

REM Wait a bit for Chrome to start
timeout /t 3 /nobreak >nul

echo ====================================
echo   [2/4] Starting Docker Services
echo ====================================
echo.

REM Stop any existing containers
docker-compose down 2>nul

REM Start Docker services (Core, Backend, Worker only - NOT WebRelay)
echo Starting Core, Backend, Worker (Docker)...
start /min cmd /c "docker-compose up --build core backend worker"

REM Start WebRelay locally (needs access to Chrome on host)
echo Starting WebRelay (Local)...
start /min cmd /c "cd webrelay && npm start"

echo Waiting for services to start...
timeout /t 15 /nobreak >nul

echo ====================================
echo   [3/4] Health Check
echo ====================================
echo.

:WAIT_CORE
echo Checking Core (Port 8001)...
curl -s http://localhost:8001/api/status >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   - Core not ready yet, waiting...
    timeout /t 2 /nobreak >nul
    goto WAIT_CORE
)
echo   - Core: Online ✓

echo Checking Backend (Port 8000)...
curl -s http://localhost:8000/ >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   - Backend not ready yet, waiting...
    timeout /t 2 /nobreak >nul
    goto WAIT_CORE
)
echo   - Backend: Online ✓

echo Checking WebRelay (Port 3000)...
curl -s http://localhost:3000/health >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   - WebRelay not ready yet, waiting...
    timeout /t 2 /nobreak >nul
    goto WAIT_CORE
)
echo   - WebRelay: Online ✓

echo Checking Chrome Debug Port (9222)...
curl -s http://localhost:9222/json/version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo   - Chrome Debug: Not available!
    echo   - Please ensure Chrome is running
) else (
    echo   - Chrome Debug: Online ✓
)

echo.
echo ====================================
echo   [4/4] Opening Dashboards
echo ====================================
echo.

REM Open Self-Loop Dashboard
echo Opening Self-Loop Dashboard...
start http://localhost:8001/static/selfloop-dashboard.html

REM Wait a moment
timeout /t 2 /nobreak >nul

REM Open Sheratan Control Dashboard (file-based)
echo Opening Sheratan Control Dashboard...
start "%CD%\sheratan-dashboard.html"

echo.
echo ====================================
echo   Sheratan Self-Loop System Ready!
echo ====================================
echo.
echo Services Running:
echo  - Core:     http://localhost:8001
echo  - Backend:  http://localhost:8000
echo  - WebRelay: http://localhost:3000
echo  - Chrome Debug: Port 9222
echo.
echo Dashboards Opened:
echo  1. Self-Loop Dashboard (Boss Directives 4 ^& 5)
echo  2. Sheratan Control Dashboard (Advanced)
echo.
echo Next Steps:
echo  1. Ensure you're logged in to ChatGPT
echo  2. Use "Start Standard Code Analysis" in Self-Loop Dashboard
echo  3. Or create custom missions
echo.
echo To stop all services: docker-compose down
echo.
pause
