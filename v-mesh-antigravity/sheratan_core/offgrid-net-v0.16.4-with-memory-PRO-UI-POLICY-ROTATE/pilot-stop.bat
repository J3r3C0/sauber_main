@echo off
setlocal
cd /d "%~dp0"
echo [pilot] Stopping related Python processes...
for /f "tokens=2 delims==;" %%P in ('wmic process where "name='python.exe' or name='pythonw.exe'" get ProcessId /value ^| find "="') do (
  for /f "usebackq tokens=*" %%C in (`wmic process where "ProcessId=%%P" get CommandLine /value ^| find "="`) do (
    echo %%C | find /I "host_daemon_simple.py" >nul && taskkill /PID %%P /F >nul
    echo %%C | find /I "radio_gateway_simple.py" >nul && taskkill /PID %%P /F >nul
    echo %%C | find /I "broker_simple.py" >nul && taskkill /PID %%P /F >nul
    echo %%C | find /I "swim_agent.py" >nul && taskkill /PID %%P /F >nul
  )
)
echo [pilot] Stop attempts issued. Close any remaining terminals manually if needed.
pause
