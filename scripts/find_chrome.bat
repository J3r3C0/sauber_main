@echo off
REM Dynamically locate Chrome executable
REM Checks both Program Files and Program Files (x86)

set "CHROME_PATH="

REM Check Program Files first
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=C:\Program Files\Google\Chrome\Application\chrome.exe"
    goto :found
)

REM Check Program Files (x86)
if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
    goto :found
)

REM Check user-local installation
if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" (
    set "CHROME_PATH=%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"
    goto :found
)

REM Not found
echo [ERROR] Google Chrome not found in standard locations
echo Please install Chrome or set CHROME_PATH manually
exit /b 1

:found
echo [INFO] Chrome found: %CHROME_PATH%
exit /b 0
