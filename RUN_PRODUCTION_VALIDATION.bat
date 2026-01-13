@echo off
REM ============================================================================
REM Sheratan Production Validation Runner
REM Starts all services and runs comprehensive validation tests
REM ============================================================================

echo [PRODUCTION VALIDATION] Starting comprehensive system validation...
echo.

REM Step 1: Stop any existing services
echo [STEP 1/4] Stopping existing services...
taskkill /F /IM python.exe /IM node.exe /IM chrome.exe /T 2>nul
timeout /t 2 /nobreak >nul
echo   Done.
echo.

REM Step 2: Start system services
echo [STEP 2/4] Starting Sheratan system...

REM Find Chrome dynamically
call "%~dp0scripts\find_chrome.bat"
if errorlevel 1 (
    echo   ERROR: Chrome not found. Please install Chrome or set CHROME_PATH manually.
    pause
    exit /b 1
)

REM Start Chrome with Remote Debugging
echo   Starting Chrome with Remote Debugging...
start "" "%CHROME_PATH%" --remote-debugging-port=9222 --user-data-dir="%TEMP%\chrome_debug_sheratan" https://chatgpt.com

REM Start WebRelay
echo   Starting WebRelay...
cd external\webrelay
start "WebRelay" cmd /c "npm start > ..\..\webrelay.log 2>&1"
cd ..\..

REM Start Core
echo   Starting Core...
start "Core" cmd /c "python -u core\main.py > core.log 2>&1"

REM Start Worker
echo   Starting Worker...
start "Worker" cmd /c "python -u worker\worker_loop.py > worker.log 2>&1"

echo   Services started. Waiting for initialization...
timeout /t 10 /nobreak >nul
echo.

REM Step 3: Verify Core API
echo [STEP 3/4] Verifying Core API...
python -c "import requests; r = requests.get('http://localhost:8001/api/missions', timeout=10); print(f'  Core API OK: {len(r.json())} missions')" 2>nul
if errorlevel 1 (
    echo   ERROR: Core API not responding!
    echo   Check core.log for details
    pause
    exit /b 1
)
echo.

REM Step 4: Run Production Validation Tests
echo [STEP 4/4] Running Production Validation Tests...
echo.
python tests\production_validation.py

REM Capture exit code
set TEST_RESULT=%ERRORLEVEL%

echo.
echo ========================================
if %TEST_RESULT%==0 (
    echo [SUCCESS] Production validation passed!
) else (
    echo [FAILURE] Production validation failed!
    echo Check logs for details:
    echo   - core.log
    echo   - worker.log
    echo   - webrelay.log
)
echo ========================================
echo.
echo Dashboard: http://localhost:3001
echo.

pause
exit /b %TEST_RESULT%
