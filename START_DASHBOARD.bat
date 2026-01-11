@echo off
REM ============================================
REM Sheratan Dashboard - Local Server
REM ============================================

echo [DASHBOARD] Starting Sheratan Dashboard...
echo.
echo Dashboard will be available at:
echo   http://localhost:8080
echo.
echo Press Ctrl+C to stop
echo.

cd dashboard
python -m http.server 8080
