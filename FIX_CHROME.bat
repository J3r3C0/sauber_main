@echo off
REM ============================================
REM Fix ChatGPT Network Error
REM Clears Chrome profile and restarts
REM ============================================

echo [FIX] Clearing Chrome profile to fix network errors...
echo.

REM Stop all services first
call STOP_SHERATAN.bat

echo.
echo [FIX] Deleting Chrome profile cache...

REM Delete Chrome profile (but keep the directory)
if exist "data\chrome_profile\Default" (
    rd /s /q "data\chrome_profile\Default"
    echo [FIX] Deleted Default profile
)

if exist "data\chrome_profile\SingletonLock" (
    del /f /q "data\chrome_profile\SingletonLock"
    echo [FIX] Deleted SingletonLock
)

if exist "data\chrome_profile\SingletonSocket" (
    del /f /q "data\chrome_profile\SingletonSocket"
    echo [FIX] Deleted SingletonSocket
)

echo.
echo ============================================
echo [FIX] Chrome profile cleared!
echo ============================================
echo.
echo Next: Start system with fresh Chrome session
echo Run: .\START_ULTIMATE.bat
echo.
pause
