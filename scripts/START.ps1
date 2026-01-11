# ============================================================================
# Sheratan Clean Build - Master Startup Script
# ============================================================================
# Starts all Sheratan components in the correct order

$ErrorActionPreference = "Continue"

# Force UTF-8 encoding
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host ""
Write-Host "             SHERATAN CLEAN BUILD - MASTER STARTUP              " -ForegroundColor Cyan
Write-Host "             (Stable Components Only)                           " -ForegroundColor Gray
Write-Host ""

# --- Configuration ---
$PROJECT_ROOT = Resolve-Path (Join-Path $PSScriptRoot "..")
$MESH_OFFGRID = Join-Path $PROJECT_ROOT "mesh\offgrid"
$EXTERNAL_WEBRELAY = Join-Path $PROJECT_ROOT "external\webrelay"
$CORE = Join-Path $PROJECT_ROOT "core"
$WORKER = Join-Path $PROJECT_ROOT "worker"
$DASHBOARD = Join-Path $PROJECT_ROOT "dashboard"
$RUNTIME = Join-Path $PROJECT_ROOT "mesh\runtime"
$EXTERNAL = Join-Path $PROJECT_ROOT "external"

# --- 0) Cleanup Previous Sessions ---
Write-Host "[0/10] Cleaning up previous Sheratan processes..." -ForegroundColor Yellow
$sh_procs = @("python", "node", "chrome", "pwsh")
foreach ($proc in $sh_procs) {
    Get-Process -Name $proc -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like "SHERATAN:*" } | ForEach-Object {
        Write-Host "  - Stopping $($_.ProcessName) (Id: $($_.Id))" -ForegroundColor Gray
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
}
Start-Sleep -Seconds 1

# --- 1) Initialization ---
Write-Host "[1/10] Initializing runtime directories..." -ForegroundColor Yellow
$dirs = @(
    "mesh\runtime\inbox",
    "mesh\runtime\queue\approved",
    "mesh\runtime\queue\blocked",
    "mesh\runtime\outbox\results",
    "mesh\runtime\logs"
)
foreach ($d in $dirs) {
    $p = Join-Path $PROJECT_ROOT $d
    if (!(Test-Path $p)) {
        New-Item -ItemType Directory -Path $p -Force | Out-Null
        Write-Host "  + Created $d" -ForegroundColor Gray
    }
}
# Create ledger if not exists
$ledger = Join-Path $PROJECT_ROOT "mesh\runtime\outbox\ledger.jsonl"
if (!(Test-Path $ledger)) {
    New-Item -ItemType File -Path $ledger -Force | Out-Null
}
Write-Host "  [OK] Runtime zones ready" -ForegroundColor Green

# --- 2) Start Core API ---
Write-Host ""
Write-Host "[2/10] Starting Core API (Port 8001)..." -ForegroundColor Yellow
$coreLog = Join-Path $RUNTIME "logs\core.log"
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = 'SHERATAN: CORE API'; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; python -m uvicorn main:app --host 0.0.0.0 --port 8001 2>&1 | Tee-Object -FilePath '$coreLog'" -WorkingDirectory $CORE
Start-Sleep -Seconds 5

# --- 3) Start Offgrid Broker ---
Write-Host ""
Write-Host "[3/10] Starting Offgrid Broker (Port 9000)..." -ForegroundColor Yellow
$brokerLog = Join-Path $RUNTIME "logs\broker.log"
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = 'SHERATAN: BROKER'; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; python broker/auction_api.py --port 9000 2>&1 | Tee-Object -FilePath '$brokerLog'" -WorkingDirectory $MESH_OFFGRID
Start-Sleep -Seconds 3

# --- 4) Start Offgrid Hosts ---
Write-Host ""
Write-Host "[4/10] Starting Offgrid Hosts..." -ForegroundColor Yellow
$nodes = @(
    @{Port = 8081; Id = "node-A" },
    @{Port = 8082; Id = "node-B" }
)

foreach ($node in $nodes) {
    Write-Host "  > Launching $($node.Id) on port $($node.Port)..." -ForegroundColor Gray
    $logFile = Join-Path $RUNTIME "logs\$($node.Id).log"
    Start-Process pwsh -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = 'SHERATAN: $($node.Id)'; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; python -m host.api_real --port $($node.Port) --node_id $($node.Id) 2>&1 | Tee-Object -FilePath '$logFile'" -WorkingDirectory $MESH_OFFGRID
}
Start-Sleep -Seconds 3

# --- 5) Start Chrome (Debug Mode) ---
Write-Host ""
Write-Host "[5/10] Starting Chrome (Port 9222)..." -ForegroundColor Yellow
$CHROME_BAT = Join-Path $PROJECT_ROOT "start_chrome.bat"
if (Test-Path $CHROME_BAT) {
    Start-Process cmd -ArgumentList @("/c", $CHROME_BAT) -WindowStyle Hidden
    Write-Host "  [OK] Chrome launched via start_chrome.bat" -ForegroundColor Green
}
else {
    Start-Process chrome -ArgumentList "--remote-debugging-port=9222", "https://chatgpt.com", "https://gemini.google.com/app"
    Write-Host "  [OK] Chrome launched with debug port" -ForegroundColor Green
}
Start-Sleep -Seconds 3

# --- 6) Start WebRelay ---
Write-Host ""
Write-Host "[6/10] Starting WebRelay (Port 3000)..." -ForegroundColor Yellow
if (Test-Path $EXTERNAL_WEBRELAY) {
    $webrelayLog = Join-Path $RUNTIME "logs\webrelay.log"
    Start-Process pwsh -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = 'SHERATAN: WEBRELAY'; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; npm start 2>&1 | Tee-Object -FilePath '$webrelayLog'" -WorkingDirectory $EXTERNAL_WEBRELAY
    Write-Host "  [OK] WebRelay starting..." -ForegroundColor Green
}
Start-Sleep -Seconds 5

# --- 7) Start Gatekeeper ---
Write-Host ""
Write-Host "[7/10] Starting Gatekeeper..." -ForegroundColor Yellow
$gatekeeperLog = Join-Path $RUNTIME "logs\gatekeeper.log"
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = 'SHERATAN: GATEKEEPER'; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; python gatekeeper.py 2>&1 | Tee-Object -FilePath '$gatekeeperLog'" -WorkingDirectory (Join-Path $EXTERNAL "gatekeeper")
Start-Sleep -Seconds 2

# --- 8) Start Auditor ---
Write-Host ""
Write-Host "[8/10] Starting Auditor..." -ForegroundColor Yellow
$auditorLog = Join-Path $RUNTIME "logs\auditor.log"
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = 'SHERATAN: AUDITOR'; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; python auditor_relay.py 2>&1 | Tee-Object -FilePath '$auditorLog'" -WorkingDirectory (Join-Path $EXTERNAL "auditor")
Start-Sleep -Seconds 2

# --- 9) Start Final Decision ---
Write-Host ""
Write-Host "[9/10] Starting Final Decision..." -ForegroundColor Yellow
$finalLog = Join-Path $RUNTIME "logs\final_decision.log"
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = 'SHERATAN: FINAL DECISION'; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; python final_decision.py 2>&1 | Tee-Object -FilePath '$finalLog'" -WorkingDirectory (Join-Path $EXTERNAL "final_decision")
Start-Sleep -Seconds 2

# --- 10) Start Worker Loop ---
Write-Host ""
Write-Host "[10/10] Starting Worker Loop..." -ForegroundColor Yellow
$workerLog = Join-Path $RUNTIME "logs\worker.log"
Start-Process pwsh -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = 'SHERATAN: WORKER'; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; python worker_loop.py 2>&1 | Tee-Object -FilePath '$workerLog'" -WorkingDirectory $WORKER
Start-Sleep -Seconds 3

# --- Verification ---
Write-Host ""
Write-Host "Verifying system status..." -ForegroundColor Yellow

$endpoints = @(
    @{Name = "Core API "; Url = "http://localhost:8001/api/status" },
    @{Name = "Broker   "; Url = "http://127.0.0.1:9000/status" },
    @{Name = "Host-A   "; Url = "http://127.0.0.1:8081/announce" },
    @{Name = "Host-B   "; Url = "http://127.0.0.1:8082/announce" },
    @{Name = "WebRelay "; Url = "http://localhost:3000/health" }
)

foreach ($ep in $endpoints) {
    try {
        $res = Invoke-WebRequest -Uri $ep.Url -Method GET -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
        Write-Host "  [PASS] $($ep.Name) online" -ForegroundColor Green
    }
    catch {
        Write-Host "  [WARN] $($ep.Name) not responding yet" -ForegroundColor Yellow
    }
}

# --- Launch Dashboard ---
Write-Host ""
Write-Host "Starting Dashboard (Port 3001)..." -ForegroundColor Cyan
if (Test-Path $DASHBOARD) {
    Start-Process pwsh -ArgumentList "-NoExit", "-Command", "`$Host.UI.RawUI.WindowTitle = 'SHERATAN: DASHBOARD'; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; npm run dev" -WorkingDirectory $DASHBOARD
    Start-Sleep -Seconds 3
    Write-Host "  [OK] Dashboard starting at http://localhost:3001" -ForegroundColor Green
}

Write-Host ""
Write-Host "[OK] SHERATAN CLEAN BUILD - BOOT COMPLETE" -ForegroundColor Green
Write-Host " All components started. Check individual windows for details."
Write-Host " Dashboard: http://localhost:3001"
Write-Host ""
