@echo off
echo [SHERATAN] Stopping all services...

taskkill /FI "WindowTitle eq Sheratan Core*" /T /F 2>nul
taskkill /FI "WindowTitle eq Journal Sync API*" /T /F 2>nul
taskkill /FI "WindowTitle eq Replica Sync*" /T /F 2>nul
taskkill /FI "WindowTitle eq Python Worker*" /T /F 2>nul
taskkill /FI "WindowTitle eq WebRelay Worker*" /T /F 2>nul
taskkill /FI "WindowTitle eq Chrome Debug*" /T /F 2>nul

echo [SHERATAN] All services stopped.
pause
