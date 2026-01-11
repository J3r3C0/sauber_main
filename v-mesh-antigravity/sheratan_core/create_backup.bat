@echo off
REM Backup Script for Sheratan Core POC
REM Creates a clean backup excluding dependencies and build artifacts

set SOURCE=c:\sheratan-core-poc
set BACKUP=c:\sheratan-core-poc-backup
set TIMESTAMP=%DATE:~-4,4%%DATE:~-10,2%%DATE:~-7,2%_%TIME:~0,2%%TIME:~3,2%%TIME:~6,2%
set TIMESTAMP=%TIMESTAMP: =0%

echo ========================================
echo Sheratan Core POC - Backup Script
echo ========================================
echo.
echo Source: %SOURCE%
echo Backup: %BACKUP%
echo Timestamp: %TIMESTAMP%
echo.

REM Create backup directory
if not exist "%BACKUP%" mkdir "%BACKUP%"

echo Creating backup...
echo.

REM Use robocopy to selectively copy files
robocopy "%SOURCE%" "%BACKUP%" /E /XD ^
    node_modules ^
    venv ^
    __pycache__ ^
    .git ^
    .pytest_cache ^
    webrelay_out ^
    webrelay_in ^
    data ^
    dist ^
    build ^
    *.egg-info ^
    /XF ^
    *.pyc ^
    *.pyo ^
    *.log ^
    *.tmp ^
    /NP /NDL /NFL

echo.
echo ========================================
echo Backup Complete!
echo ========================================
echo Location: %BACKUP%
echo.
echo Excluded directories:
echo   - node_modules (npm packages)
echo   - venv (Python virtual environment)
echo   - __pycache__ (Python cache)
echo   - .git (Git repository)
echo   - webrelay_out/in (Runtime data)
echo   - data (Database files)
echo.

pause
