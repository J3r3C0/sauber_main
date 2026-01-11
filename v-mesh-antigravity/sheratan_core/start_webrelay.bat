@echo off
echo.
echo ====================================
echo Starting Sheratan WebRelay
echo ====================================
echo.

echo [INFO] WebRelay connects Core to ChatGPT via Chrome Debug Protocol
echo.

REM Check if Chrome is running in debug mode
curl -s http://localhost:9222/json/version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Chrome Debug Port (9222) not accessible!
    echo.
    echo Please start Chrome in debug mode first:
    echo   start_chrome.bat
    echo.
    echo Or continue anyway (WebRelay will wait for Chrome)...
    echo.
    choice /C YN /M "Continue anyway"
    if %ERRORLEVEL% EQU 2 exit /b 1
)

echo.
echo [1/3] Checking Node.js installation...
where node >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Node.js not found!
    echo Please install Node.js: https://nodejs.org
    pause
    exit /b 1
)

echo [2/3] Navigating to WebRelay directory...
cd /d "%~dp0webrelay"
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] WebRelay directory not found!
    pause
    exit /b 1
)

echo [3/3] Starting WebRelay service...
echo.
echo ====================================
echo WebRelay is starting...
echo ====================================
echo.
echo Service URL: http://localhost:3000
echo Health Check: http://localhost:3000/health
echo.
echo Press Ctrl+C to stop WebRelay
echo.

npm start
