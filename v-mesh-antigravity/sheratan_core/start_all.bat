@echo off
echo.
echo ================================================
echo   Sheratan Complete System Startup
echo ================================================
echo.
echo Starting all services in separate windows...
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

echo.
echo ====================================
echo   Starting Chrome in Debug Mode
echo ====================================
echo.

REM Start Chrome in debug mode
start chrome --remote-debugging-port=9222 --remote-debugging-address=0.0.0.0 --remote-allow-origins=* --user-data-dir="%TEMP%\chrome-sheratan-debug"

echo Chrome started on port 9222
echo Please log in to https://chatgpt.com
echo.
timeout /t 5 /nobreak >nul

REM 1. Start All Docker Services (Core + Backend + Worker + WebRelay)
echo [1/2] Starting All Docker Services...
start "Sheratan - Docker Services" cmd /k "%~dp0start_core.bat"
timeout /t 15 /nobreak >nul

REM 2. Open Dashboard
echo [2/2] Opening Dashboard...
start "Sheratan - Dashboard" cmd /k "%~dp0start_dashboard.bat"

echo.
echo ================================================
echo   All services are starting!
echo ================================================
echo.
echo Services started:
echo  1. Chrome Debug (Port 9222) - automatic
echo  2. Docker Services (Core, Backend, Worker, WebRelay)
echo  3. Dashboard (Browser)
echo.
echo Dashboard URL: http://localhost:8001/static/selfloop-dashboard.html
echo.
echo To stop all services:
echo  - docker-compose down
echo.
echo This window will close in 10 seconds...
echo This window will close in 10 seconds...
timeout /t 10 /nobreak
