@echo off
setlocal
cd /d "%~dp0"

echo [pilot] Real-mode start (UDP multicast + FastAPI + optional signed beacons)
echo [pilot] Ensure venv + deps: pip install -r requirements.txt
echo.
start "Host A (api_real)" cmd /k python host_daemon\api_real.py --port 8081 --node_id node-A
start "Host B (api_real)" cmd /k python host_daemon\api_real.py --port 8082 --node_id node-B
set "OFFGRID_SK_B64="
start "Radio A (real)" cmd /k python radio\radio_gateway_real.py --node_id node-A --endpoint http://127.0.0.1:8081 --interval 3 --ed25519_sk_b64 %OFFGRID_SK_B64%
start "Radio B (real)" cmd /k python radio\radio_gateway_real.py --node_id node-B --endpoint http://127.0.0.1:8082 --interval 3 --ed25519_sk_b64 %OFFGRID_SK_B64%
start "Broker (real)" cmd /k python broker\broker_real.py --interval 4
echo.
echo [pilot] Real-mode launched. Use pilot-auswertung.bat for report, pilot-stop.bat to stop.
pause
