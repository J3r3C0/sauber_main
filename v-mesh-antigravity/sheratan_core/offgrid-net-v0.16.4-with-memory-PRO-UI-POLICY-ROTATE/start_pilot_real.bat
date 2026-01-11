
@echo off
setlocal

if not exist .venv (
  py -m venv .venv || goto :err
)
call .venv\Scripts\activate || goto :err
python -m pip install --upgrade pip
pip install -r requirements.txt || goto :err

REM Start API
start "HOST API" cmd /k "call .venv\Scripts\activate && python -m host_daemon.api_real --config config\config.yaml"

REM Start Radio (replace --node_id/--endpoint as needed)
start "RADIO" cmd /k "call .venv\Scripts\activate && python -m radio.radio_gateway_real --node_id demo --endpoint http://127.0.0.1:8081 --group 239.23.0.7 --port 47007 --interval 3.0"
exit /b 0

:err
echo [ERROR] Failed to start pilot.
pause
exit /b 1
