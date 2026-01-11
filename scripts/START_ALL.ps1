# ============================================================================
# Sheratan - Production-Ready Start Script
# ============================================================================
# Starts all components in the background with centralized logging.

$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ROOT = $PSScriptRoot
if ($ROOT -eq "") { $ROOT = Get-Location }
$PROJECT_ROOT = Resolve-Path (Join-Path $ROOT "..")
$LOG_DIR = New-Item -ItemType Directory -Force -Path (Join-Path $PROJECT_ROOT "logs")

function Start-SheratanComponent {
    param(
        [string]$Name,
        [string]$Cwd,
        [string]$Command,
        [string]$Args
    )
    Write-Host "🚀 Starting $Name..." -ForegroundColor Cyan
    $logFile = Join-Path $LOG_DIR "$($Name.Replace(' ', '_')).log"
    
    # Start process and redirect output
    Start-Process pwsh -ArgumentList "-Command", "cd '$Cwd'; $Command $Args 2>&1 | Tee-Object -FilePath '$logFile'\" -WindowStyle Hidden
}

Write-Host ""
Write-Host "SHERATAN CLEAN BUILD - STARTING ALL SERVICES" -ForegroundColor Green
Write-Host "Logs are being written to: $($LOG_DIR.FullName)"
Write-Host ""

# 1. CORE API
Start-SheratanComponent -Name "Core API" -Cwd "$PROJECT_ROOT\core" -Command "python" -Args "-m uvicorn main:app --host 0.0.0.0 --port 8001"

# 2. BROKER
Start-SheratanComponent -Name "Broker" -Cwd "$PROJECT_ROOT\mesh\offgrid" -Command "python" -Args "broker/auction_api.py --port 9000"

# 3. HOST A
Start-SheratanComponent -Name "Host A" -Cwd "$PROJECT_ROOT\mesh\offgrid" -Command "python" -Args "host/api_real.py --port 8081 --node_id host_a"

# 4. WEBRELAY
Start-SheratanComponent -Name "WebRelay" -Cwd "$PROJECT_ROOT\external\webrelay" -Command "npm" -Args "start"

# 5. DASHBOARD (Vite)
Start-SheratanComponent -Name "Dashboard" -Cwd "$PROJECT_ROOT\external\dashboard" -Command "npm" -Args "run dev"

# 6. WORKER LOOP
Start-SheratanComponent -Name "Worker" -Cwd "$PROJECT_ROOT\worker" -Command "python" -Args "worker_loop.py"

Write-Host ""
Write-Host "✅ All components started in background." -ForegroundColor Green
Write-Host "Checking health in 5 seconds..."
Start-Sleep -Seconds 5

# Quick verification
Write-Host ""
Write-Host "SERVICE STATUS:" -ForegroundColor Yellow
$services = @{
    "Core API"  = "http://localhost:8001/api/status"
    "Broker"    = "http://localhost:9000/status"
    "WebRelay"  = "http://localhost:3000/health"
    "Host A"    = "http://localhost:8081/status"
    "Dashboard" = "http://localhost:3001"
}

foreach ($s in $services.Keys) {
    try {
        $res = Invoke-RestMethod -Uri $services[$s] -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
        Write-Host "  [OK] $s" -ForegroundColor Green
    }
    catch {
        Write-Host "  [??] $s (Not responding yet or failed)" -ForegroundColor Gray
    }
}

Write-Host ""
Write-Host "Use .\scripts\STOP_SHERATAN.ps1 to stop all services."
