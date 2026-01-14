@echo off
REM E2E Test Runner - Tests Spec→Job pipeline with system start/stop

echo ========================================
echo E2E Test Suite: Spec-to-Job Pipeline
echo ========================================
echo.

REM 1. Ensure system is stopped
echo [1/4] Ensuring clean state...
taskkill /F /IM python.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul
echo   ✓ System stopped

REM 2. Start system
echo [2/4] Starting system...
start "Sheratan Core" cmd /c "python -m core.main"
timeout /t 5 /nobreak >nul
echo   ✓ System started (5s warmup)

REM 3. Run tests
echo [3/4] Running E2E tests...
echo.
python tests\e2e_spec_to_job.py
set TEST_RESULT=%ERRORLEVEL%

REM 4. Stop system
echo.
echo [4/4] Stopping system...
taskkill /F /IM python.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul
echo   ✓ System stopped

echo.
echo ========================================
if %TEST_RESULT% EQU 0 (
    echo ✅ ALL TESTS PASSED
    echo Ready for Asymmetry scoping!
) else (
    echo ❌ TESTS FAILED
    echo Check output above for details
)
echo ========================================
echo.

pause
exit /b %TEST_RESULT%
