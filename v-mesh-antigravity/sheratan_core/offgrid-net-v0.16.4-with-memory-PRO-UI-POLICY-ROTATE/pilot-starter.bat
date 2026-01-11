@echo off
setlocal
cd /d "%~dp0"

echo [pilot] Generating keys if needed...
IF NOT EXIST ".\keys\node-A.json" ( python -m keys.key_utils --node_id node-A 2>nul )
IF NOT EXIST ".\keys\node-B.json" ( python -m keys.key_utils --node_id node-B 2>nul )

echo [pilot] Starting services in visible terminals...

REM -- Host daemons (simple)
start "Host A (simple)" cmd /k python scripts\host_daemon_simple.py --port 8081 --node_id node-A --keys .\keys\node-A.json
start "Host B (simple)" cmd /k python scripts\host_daemon_simple.py --port 8082 --node_id node-B --keys .\keys\node-B.json

REM -- Radio beacons (simple, simulate peer visibility)
start "Radio A" cmd /k python scripts\radio_gateway_simple.py --node_id node-A --endpoint http://127.0.0.1:8081 --peer http://127.0.0.1:8082 --interval 3
start "Radio B" cmd /k python scripts\radio_gateway_simple.py --node_id node-B --endpoint http://127.0.0.1:8082 --peer http://127.0.0.1:8081 --interval 3

REM -- SWIM heartbeat (optional)
start "SWIM" cmd /k python scripts\swim_agent.py --node_id cluster-1 --interval 5

REM -- Broker (simple)
start "Broker (simple)" cmd /k python scripts\broker_simple.py --sleep 4

echo.
echo [pilot] All components launched in separate terminals.
echo [pilot] Use 'pilot-upload.bat' to trigger a test upload.
echo [pilot] Use 'pilot-auswertung.bat' for report/asserts, and 'pilot-stop.bat' to stop.
pause
