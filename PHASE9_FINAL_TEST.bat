@echo off
REM ============================================
REM Phase 9 Complete Test - Clean Start
REM ============================================

echo [PHASE9] Clean Start + Test
echo.

REM Step 1: Kill all processes
echo [1/5] Stopping all services...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM node.exe 2>nul
taskkill /F /IM chrome.exe 2>nul
timeout /t 3 /nobreak >nul
echo   Done.
echo.

REM Step 2: Start Core API
echo [2/5] Starting Core API...
cd /d "%~dp0"
start /MIN "Core" cmd /c "python -m uvicorn core.main:app --host 0.0.0.0 --port 8001 2>nul"
timeout /t 5 /nobreak >nul
echo   Done.
echo.

REM Step 3: Start Worker (will load .env)
echo [3/5] Starting Worker...
start /MIN "Worker" cmd /c "python worker\worker_loop.py 2>nul"
timeout /t 3 /nobreak >nul
echo   Done.
echo.

REM Step 4: Start WebRelay
echo [4/5] Starting WebRelay...
start /MIN "WebRelay" cmd /c "cd external\webrelay && npm start 2>nul"
timeout /t 8 /nobreak >nul
echo   Done.
echo.

REM Step 5: Run Test
echo [5/5] Running Phase 9 Test 1...
echo.
python tests\phase9_test1_walk_tree.py

echo.
echo ========================================
echo Test Complete!
echo ========================================
pause
