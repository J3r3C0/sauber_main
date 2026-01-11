#Sheratan Complete System Startup

Write - Host "Starting Sheratan System..." -
    ForegroundColor Cyan

# 1. Check Docker
    try {
  docker ps | Out - Null Write - Host " Docker OK" - ForegroundColor Green
} catch {
  Write - Host " Start Docker Desktop first!" - ForegroundColor Red exit 1
}

# 1. Start Chrome in Debug Mode
Write - Host "Starting Chrome in Debug Mode..." - ForegroundColor Yellow Start -
    Process chrome - ArgumentList "--remote-debugging-port=9222",
    "--remote-debugging-address=0.0.0.0", "--remote-allow-origins=*",
    "--user-data-dir=$env:TEMP\chrome-sheratan-debug" Write -
        Host "Chrome started on port 9222" - ForegroundColor Green Write -
        Host "Please log in to https://chatgpt.com" -
        ForegroundColor Cyan Start -
        Sleep 5

# 2. Start Docker services
        Write -
        Host "Starting Docker containers..." - ForegroundColor Yellow docker -
        compose up - d core worker Start -
        Sleep 5

# 3. Start Backend
        Write -
        Host "Starting Backend..." - ForegroundColor Yellow Start -
        Process powershell - ArgumentList "-NoExit",
    "-Command",
    "cd C:\sheratan-core-poc\backend; uvicorn main:app --host 0.0.0.0 --port "
    "8000 --reload" Start -
        Sleep 3

# 4. Start WebRelay
        Write -
        Host "Starting WebRelay..." - ForegroundColor Yellow Start -
        Process powershell - ArgumentList "-NoExit",
    "-Command",
    "cd C:\sheratan-core-poc\webrelay; npm start" Start -
        Sleep 5

# 5. Start Dashboard
        Write -
        Host "Starting Dashboard..." - ForegroundColor Yellow Start -
        Process powershell - ArgumentList "-NoExit",
    "-Command",
    "cd C:\sheratan-core-poc\react-dashboard; npm run dev" Start -
        Sleep 5

        Write -
        Host " All services started!" - ForegroundColor Green Write -
        Host "Dashboard: http://localhost:5174" -
        ForegroundColor Cyan

            Start -
        Process "http://localhost:5174"
