@echo off
setlocal
cd /d "%~dp0"
echo [pilot] Report:
python scripts\pilot_report.py
echo.
echo [pilot] Assertions:
python pilot_assert.py --expected-nodes node-A,node-B --min-receipts 1 --min-rep 0.45
echo.
echo [pilot] Finished. Press any key.
pause >nul
