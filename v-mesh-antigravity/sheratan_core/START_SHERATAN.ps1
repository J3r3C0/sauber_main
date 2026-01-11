# ============================================================================
# Sheratan Offgrid - Complete Startup Script
# ============================================================================
# Starts all services in correct order with proper error handling

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║         SHERATAN OFFGRID - COMPLETE STARTUP                ║" -ForegroundColor Cyan
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Configuration
$basePath = "C:\Projects\2_sheratan_core"
$offgridPath = "$basePath\offgrid-net-v0.16.4-with-memory-PRO-UI-POLICY-ROTATE"
$corePath = "$basePath\core"

# Verify paths exist
Write-Host "[1/6] Verifying paths..." -ForegroundColor Yellow
if (-not (Test-Path $offgridPath)) {
    Write-Host "  ✗ Offgrid path not found: $offgridPath" -ForegroundColor Red
    exit 1
}
if (-not (Test-Path $corePath)) {
    Write-Host "  ✗ Core path not found: $corePath" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ All paths verified" -ForegroundColor Green



# Start Host A
Write-Host ""
Write-Host "[2/6] Starting Offgrid Host-A (Port 8081)..." -ForegroundColor Yellow
Start-Process pwsh -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$offgridPath'; Write-Host '=== HOST-A (Port 8081) ===' -ForegroundColor Cyan; python -m host_daemon.daemon_stub --port 8081 --node_id node-A"
)
Start-Sleep -Seconds 2
Write-Host "  ✓ Host-A terminal launched" -ForegroundColor Green

# Start Host B
Write-Host ""
Write-Host "[3/6] Starting Offgrid Host-B (Port 8082)..." -ForegroundColor Yellow
Start-Process pwsh -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$offgridPath'; Write-Host '=== HOST-B (Port 8082) ===' -ForegroundColor Cyan; python -m host_daemon.daemon_stub --port 8082 --node_id node-B"
)
Start-Sleep -Seconds 2
Write-Host "  ✓ Host-B terminal launched" -ForegroundColor Green

# Start Broker
Write-Host ""
Write-Host "[4/6] Starting Offgrid Broker (Port 9000)..." -ForegroundColor Yellow
Start-Process pwsh -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$offgridPath'; Write-Host '=== BROKER (Port 9000) ===' -ForegroundColor Cyan; python broker/auction_api.py --port 9000"
)
Start-Sleep -Seconds 3
Write-Host "  ✓ Broker terminal launched" -ForegroundColor Green

# Start Core
Write-Host ""
Write-Host "[5/6] Starting Sheratan Core (Port 8001)..." -ForegroundColor Yellow
Start-Process pwsh -ArgumentList @(
    "-NoExit",
    "-Command",
    "cd '$corePath'; Write-Host '=== CORE (Port 8001) ===' -ForegroundColor Cyan; python -m uvicorn sheratan_core_v2.main:app --host 0.0.0.0 --port 8001"
)
Start-Sleep -Seconds 5
Write-Host "  ✓ Core terminal launched" -ForegroundColor Green

# Verify all services are responding
Write-Host ""
Write-Host "[6/6] Verifying services are online..." -ForegroundColor Yellow

$services = @(
    @{Name="Host-A    "; Url="http://127.0.0.1:8081/announce"; Port=8081},
    @{Name="Host-B    "; Url="http://127.0.0.1:8082/announce"; Port=8082},
    @{Name="Broker    "; Url="http://127.0.0.1:9000/status"; Port=9000},
    @{Name="Core      "; Url="http://localhost:8001/api/status"; Port=8001}
)

$allOk = $true
$maxRetries = 10
$retryDelay = 1

foreach ($service in $services) {
    $success = $false
    for ($i = 1; $i -le $maxRetries; $i++) {
        try {
            $response = Invoke-WebRequest -Uri $service.Url -Method GET -TimeoutSec 2 -ErrorAction Stop
            if ($response.StatusCode -eq 200) {
                Write-Host "  ✓ $($service.Name) (Port $($service.Port))" -ForegroundColor Green
                $success = $true
                break
            }
        } catch {
            if ($i -lt $maxRetries) {
                Start-Sleep -Seconds $retryDelay
            }
        }
    }
    
    if (-not $success) {
        Write-Host "  ✗ $($service.Name) (Port $($service.Port)) - Not responding after $maxRetries attempts" -ForegroundColor Red
        $allOk = $false
    }
}

Write-Host ""
if ($allOk) {
    Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "║              ✓✓✓ ALL SERVICES ONLINE ✓✓✓                  ║" -ForegroundColor Green
    Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Write-Host "Services running:" -ForegroundColor Cyan
    Write-Host "  • Host-A:  http://127.0.0.1:8081" -ForegroundColor White
    Write-Host "  • Host-B:  http://127.0.0.1:8082" -ForegroundColor White
    Write-Host "  • Broker:  http://127.0.0.1:9000" -ForegroundColor White
    Write-Host "  • Core:    http://localhost:8001" -ForegroundColor White
    Write-Host ""
    Write-Host "Run integration test:" -ForegroundColor Cyan
    Write-Host "  .\simple_test.ps1" -ForegroundColor Yellow
    Write-Host ""
} else {
    Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Yellow
    Write-Host "║           ⚠ SOME SERVICES FAILED TO START ⚠               ║" -ForegroundColor Yellow
    Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Check the terminal windows for error messages." -ForegroundColor Yellow
    Write-Host "Common issues:" -ForegroundColor Cyan
    Write-Host "  • Port already in use (kill existing processes)" -ForegroundColor White
    Write-Host "  • Missing Python dependencies (pip install -r requirements.txt)" -ForegroundColor White
    Write-Host "  • Wrong working directory" -ForegroundColor White
    Write-Host ""
}

Write-Host "Press any key to exit..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
