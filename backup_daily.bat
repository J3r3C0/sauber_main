@echo off
REM ============================================
REM Sheratan Daily Backup Script
REM ============================================

set BACKUP_DIR=backup\%date:~-4,4%-%date:~-10,2%-%date:~-7,2%_%time:~0,2%-%time:~3,2%

echo [BACKUP] Creating backup directory: %BACKUP_DIR%
mkdir "%BACKUP_DIR%" 2>nul

echo [BACKUP] Backing up ledger files...
copy ledger.json "%BACKUP_DIR%\" >nul
copy ledger_events.jsonl "%BACKUP_DIR%\" >nul

echo [BACKUP] Backing up mesh registry...
copy mesh\registry\workers.json "%BACKUP_DIR%\" >nul

echo [BACKUP] Backing up worker state...
copy worker_state_*.db "%BACKUP_DIR%\" 2>nul

echo.
echo [BACKUP] ✓ Backup completed: %BACKUP_DIR%
echo.
pause
