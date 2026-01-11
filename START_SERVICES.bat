@echo off
set SHERATAN_LLM_BASE_URL=http://localhost:3000/api/job/submit
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%CD%\data\chrome_profile"
start /b "Sheratan-WebRelay" cmd /c "cd external\webrelay && npm start"
start /b "Sheratan-Core" cmd /c "cd core && python -m uvicorn main:app --host 0.0.0.0 --port 8001"
start /b "Sheratan-Broker" cmd /c "python mesh\offgrid\broker\auction_api.py --port 9000"
start /b "Sheratan-HostA" cmd /c "python mesh\offgrid\host\api_real.py --port 8081 --node_id node-A"
start /b "Sheratan-Dashboard" cmd /c "cd dashboard && npm run dev -- --host"
start /b "Sheratan-Worker" cmd /c "python worker\worker_loop.py"
echo Systems started in background.
