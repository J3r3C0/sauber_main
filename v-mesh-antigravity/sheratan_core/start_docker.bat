@echo off
echo.
echo ================================================
echo   Sheratan DOCKER Setup
echo   (Sheratan Dashboard + All Docker Services)
echo ================================================
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

REM 1. Start Chrome in Debug Mode
echo [1/3] Starting Chrome in Debug Mode...
start chrome --remote-debugging-port=9222 --remote-debugging-address=0.0.0.0 --remote-allow-origins=* --user-data-dir="%TEMP%\chrome-sheratan-debug"
echo Chrome started on port 9222
echo Please log in to https://chatgpt.com
echo.
timeout /t 5 /nobreak >nul

REM 2. Start ALL Docker Services
echo [2/3] Starting ALL Docker Services...
docker-compose up -d backend core worker webrelay
echo.
echo Waiting for services to start...
timeout /t 12 /nobreak >nul

REM 3. Check status
echo [3/3] Checking service status...
docker-compose ps

echo.
echo ================================================
echo   DOCKER Setup Complete!
echo ================================================
echo.
echo Services (ALL in Docker):
echo  - Chrome Debug:  Port 9222 (automatic)
echo  - Core:          http://localhost:8001
echo  - Backend:       http://localhost:8000
echo  - WebRelay:      http://localhost:3000
echo  - Worker:        Background
echo.
echo Opening Sheratan Dashboard...
start http://localhost:8001/static/sheratan-dashboard.html
echo.
echo Dashboard URL: http://localhost:8001/static/sheratan-dashboard.html
echo.
echo To stop: docker-compose down
echo.
pause
