@echo off
REM ============================================
REM Sheratan STOP - Fixed Version
REM Kills processes by name, not window title
REM ============================================

echo [SHERATAN] Stopping all services...

REM Kill Python processes (Core, Worker, Journal)
taskkill /F /IM python.exe 2>nul

REM Kill Node processes (WebRelay, Dashboard)
taskkill /F /IM node.exe 2>nul

REM Kill Chrome Debug
taskkill /F /IM chrome.exe 2>nul

REM Wait a moment
timeout /t 2 /nobreak >nul

echo [SHERATAN] All services stopped.
