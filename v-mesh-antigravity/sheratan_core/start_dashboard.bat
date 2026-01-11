@echo off
echo.
echo ====================================
echo Opening Sheratan Dashboard
echo ====================================
echo.

REM Check if Core is running
curl -s http://localhost:8001/api/status >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Core is not running on port 8001!
    echo.
    echo Please start Core first:
    echo   start_core.bat
    echo.
    echo Or the dashboard will show "Offline" status...
    echo.
    timeout /t 3 >nul
)

echo Opening Self-Loop Dashboard in browser...
echo URL: http://localhost:8001/static/selfloop-dashboard.html
echo.

start http://localhost:8001/static/selfloop-dashboard.html

echo.
echo Dashboard opened!
echo If page doesn't load, make sure Core is running.
echo.
