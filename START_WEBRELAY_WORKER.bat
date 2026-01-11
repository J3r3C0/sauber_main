@echo off
REM ============================================
REM WebRelay Worker Start Script (Windows)
REM ============================================

echo [WEBRELAY] Starting WebRelay Worker...
echo.

cd external\webrelay

REM Build TypeScript
echo [WEBRELAY] Building TypeScript...
call npm run build

if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo.
echo [WEBRELAY] Starting worker...
start "WebRelay Worker" cmd /k "npm start"

cd ..\..

echo.
echo ============================================
echo [WEBRELAY] Worker is ACTIVE
echo ============================================
echo.
echo WebRelay Worker is now running
echo It will process LLM jobs via ChatGPT/Claude
echo.
echo To stop: Close the "WebRelay Worker" window or run STOP_SHERATAN.bat
echo.
pause
