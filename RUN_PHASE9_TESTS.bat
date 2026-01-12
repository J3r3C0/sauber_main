@echo off
REM ============================================
REM Phase 9 E2E Test Runner - FIXED
REM ============================================

echo [PHASE9] Starting E2E Test Runner...
echo.

REM Step 1: Stop all services
echo [STEP 1/4] Stopping all services...
taskkill /F /IM python.exe 2>nul
taskkill /F /IM node.exe 2>nul
taskkill /F /IM chrome.exe 2>nul
timeout /t 3 /nobreak >nul
echo   Done.
echo.

REM Step 2: Start system in background
echo [STEP 2/4] Starting Sheratan system...
cd /d "%~dp0"

REM 1. Start Chrome with Remote Debugging (for WebRelay)
echo   Starting Chrome with Remote Debugging...
start /MIN "Chrome" cmd /c "start_chrome.bat"
timeout /t 10 /nobreak >nul

REM 2. Start WebRelay (for LLM calls)
start /MIN "WebRelay" cmd /c "cd external\webrelay && npm start > webrelay.log 2>&1"
timeout /t 10 /nobreak >nul

REM 3. Start Core API
start /MIN "Core" cmd /c "python -u -m uvicorn core.main:app --host 0.0.0.0 --port 8001 2>nul"
timeout /t 5 /nobreak >nul

REM 4. Start Worker
start /MIN "Worker" cmd /c "python -u worker\worker_loop.py > worker.log 2>&1"
timeout /t 5 /nobreak >nul

REM 5. Start Dashboard
start /MIN "Dashboard" cmd /c "cd external\dashboard && npm run dev 2>nul"
timeout /t 5 /nobreak >nul

echo   Services started. Waiting for initialization...
timeout /t 10 /nobreak >nul
echo.

REM Step 3: Verify Core API
echo [STEP 3/4] Verifying Core API...
python -c "import requests; r = requests.get('http://localhost:8001/api/status', timeout=5); print('  Core API OK:', r.json())" 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo   [WARNING] Core API not responding, waiting 10 more seconds...
    timeout /t 10 /nobreak >nul
)
echo.

REM Step 4: Run Tests
echo [STEP 4/4] Running Phase 9 E2E Tests...
echo.

echo ========================================
echo Test 1: walk_tree
echo ========================================
python tests\phase9_test1_walk_tree.py
echo.

echo ========================================
echo Test 2: batch chain
echo ========================================
python tests\phase9_test2_batch_chain.py
echo.

echo ========================================
echo Test 3: loop guards
echo ========================================
python tests\phase9_test3_loop_guards.py
echo.

echo ========================================
echo [COMPLETE] All tests finished!
echo ========================================
echo.
echo Dashboard: http://localhost:3001
echo.
pause
