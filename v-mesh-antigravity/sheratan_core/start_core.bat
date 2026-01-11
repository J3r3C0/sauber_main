@echo off
echo.
echo ====================================
echo Starting Sheratan Core System
echo ====================================
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

echo [1/3] Starting Docker Compose services (Core + Backend + Worker + WebRelay)...
docker-compose up -d backend core worker webrelay

echo.
echo [2/3] Waiting for services to be ready...
timeout /t 10 /nobreak >nul

echo.
echo [3/3] Checking service status...
docker-compose ps

echo.
echo ====================================
echo Sheratan Core System Started!
echo ====================================
echo.
echo Services:
echo  - Core:     http://localhost:8001
echo  - Backend:  http://localhost:8000
echo  - WebRelay: http://localhost:3000
echo  - Worker:   Running in background
echo.
echo Dashboard URL:
echo  - Self-Loop Dashboard: http://localhost:8001/static/selfloop-dashboard.html
echo.
echo Logs anzeigen: docker-compose logs -f
echo System stoppen: docker-compose down
echo.
pause
