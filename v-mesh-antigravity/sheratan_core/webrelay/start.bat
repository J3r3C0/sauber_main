@echo off
echo.
echo ====================================
echo Sheratan WebRelay Worker
echo ====================================
echo.

cd /d %~dp0

echo [1/3] Installing dependencies...
call npm install
if errorlevel 1 (
    echo ERROR: npm install failed
    pause
    exit /b 1
)

echo.
echo [2/3] Building TypeScript...
call npm run build
if errorlevel 1 (
    echo ERROR: Build failed
    pause
    exit /b 1
)

echo.
echo [3/3] Starting WebRelay Worker...
echo.
call npm start
