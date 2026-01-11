@echo off
REM Quick Worker Restart + Test

echo [1/3] Stopping Worker...
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Python Worker*" 2>nul
taskkill /F /IM python.exe /FI "WINDOWTITLE eq Worker*" 2>nul
timeout /t 2 /nobreak >nul

echo [2/3] Starting Worker with .env...
cd /d "%~dp0"
start /MIN "Worker" cmd /c "python worker\worker_loop.py"
timeout /t 5 /nobreak >nul

echo [3/3] Running Test 1...
python tests\phase9_test1_walk_tree.py

echo.
echo Done! Check output above.
pause
