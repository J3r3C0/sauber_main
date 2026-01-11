# ============================================================================
# Sheratan - Production Launch Pad
# ============================================================================
$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host ""
Write-Host "SHERATAN - FULL STACK STARTUP" -ForegroundColor Cyan
Write-Host "============================" -ForegroundColor Cyan
Write-Host ""

$PROJECT_ROOT = Resolve-Path "."

# 1. Cleaning and Preparation
Write-Host "[1/6] Cleaning up previous processes..." -ForegroundColor Yellow
$CHROME_BIN = "C:\Program Files\Google\Chrome\Application\chrome.exe"
Get-Process | Where-Object { $_.CommandLine -match "uvicorn|worker_loop|auction_api|api_real" } | Stop-Process -Force -ErrorAction SilentlyContinue
# Note: Keeping the active npm start if possible, or restarting it
# Get-Process | Where-Object { $_.CommandLine -match "webrelay" } | Stop-Process -Force -ErrorAction SilentlyContinue

# 2. Start Chrome (Debug Mode)
Write-Host "[2/6] Starting Chrome (Debug Port 9222)..." -ForegroundColor Green
Start-Process $CHROME_BIN -ArgumentList "--remote-debugging-port=9222", "--user-data-dir=$PROJECT_ROOT\data\chrome_profile"

# 3. Start WebRelay
Write-Host "[3/6] Starting WebRelay (Port 3000)..." -ForegroundColor Green
Start-Process "cmd" -ArgumentList "/k cd external\webrelay && npm start"

# 3. Start Core API
Write-Host "[3/6] Starting Core API (Port 8001)..." -ForegroundColor Green
Start-Process "cmd" -ArgumentList "/k cd core && python -m uvicorn main:app --host 0.0.0.0 --port 8001"

# 4. Start Broker
Write-Host "[4/6] Starting Support Services (Broker/Host)..." -ForegroundColor Yellow
Start-Process "cmd" -ArgumentList "/c python mesh\offgrid\broker\auction_api.py --port 9000" -WindowStyle Minimized
Start-Process "cmd" -ArgumentList "/c python mesh\offgrid\host\api_real.py --port 8081 --node_id node-A" -WindowStyle Minimized

# 5. Start Dashboard
Write-Host "[5/6] Starting Dashboard (Port 5173)..." -ForegroundColor Green
Start-Process "cmd" -ArgumentList "/k cd dashboard && npm run dev -- --host"

# 6. Start Worker Loop
Write-Host "[6/6] Starting Worker Loop..." -ForegroundColor Green
Start-Process "cmd" -ArgumentList "/k set SHERATAN_LLM_BASE_URL=http://localhost:3000/api/job/submit && python worker\worker_loop.py"

Write-Host ""
Write-Host "Sheratan launched! Check the new terminal windows." -ForegroundColor Cyan
Write-Host "Use 'mobile_cli.py status' to verify connection."
Write-Host ""
