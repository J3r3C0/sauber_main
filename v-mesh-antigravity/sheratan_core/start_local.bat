@echo off
echo.
echo ================================================
echo   Sheratan LOCAL Setup
echo   (Selfloop Dashboard + Local Services)
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
echo [1/4] Starting Chrome in Debug Mode...
start chrome --remote-debugging-port=9222 --remote-debugging-address=0.0.0.0 --remote-allow-origins=* --user-data-dir="%TEMP%\chrome-sheratan-debug"
echo Chrome started on port 9222
echo Please log in to https://chatgpt.com
echo.
timeout /t 5 /nobreak >nul

REM 2. Start Core in Docker
echo [2/4] Starting Core (Docker)...
docker-compose up -d core worker
timeout /t 8 /nobreak >nul

REM 3. Start Local Backend (Port 8088)
echo [3/4] Starting Local Backend on port 8088...
start "Sheratan - Local Backend" powershell -NoExit -Command "cd '%~dp0backend'; uvicorn main:app --host 0.0.0.0 --port 8088 --reload"
timeout /t 3 /nobreak >nul

REM 4. Start Local WebRelay
echo [4/4] Starting Local WebRelay...
start "Sheratan - Local WebRelay" powershell -NoExit -Command "cd '%~dp0webrelay'; npm start"
timeout /t 5 /nobreak >nul

echo.
echo ================================================
echo   LOCAL Setup Complete!
echo ================================================
echo.
echo Services:
echo  - Chrome Debug:  Port 9222 (automatic)
echo  - Core:          http://localhost:8001 (Docker)
echo  - Backend:       http://localhost:8088 (LOCAL)
echo  - WebRelay:      http://localhost:3000 (LOCAL)
echo  - Worker:        Docker (background)
echo.
echo Opening Selfloop Dashboard...
start http://localhost:8001/static/selfloop-dashboard.html
echo.
echo Dashboard URL: http://localhost:8001/static/selfloop-dashboard.html
echo.
echo To stop:
echo  - Close Backend and WebRelay windows (Ctrl+C)
echo  - Run: docker-compose down
echo.
pause
