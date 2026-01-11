# ============================================================================
# Sheratan Offgrid - Stop All Services
# ============================================================================
# Stops all running Sheratan services

Write-Host ""
Write-Host "╔════════════════════════════════════════════════════════════╗" -ForegroundColor Red
Write-Host "║         SHERATAN OFFGRID - STOP ALL SERVICES               ║" -ForegroundColor Red
Write-Host "╚════════════════════════════════════════════════════════════╝" -ForegroundColor Red
Write-Host ""

# Find and kill processes by port
$ports = @(8081, 8082, 9000, 8001)
$processesKilled = 0

Write-Host "Searching for processes on ports: $($ports -join ', ')..." -ForegroundColor Yellow
Write-Host ""

foreach ($port in $ports) {
    try {
        # Find process using the port
        $connections = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue
        
        foreach ($conn in $connections) {
            $processId = $conn.OwningProcess
            $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
            
            if ($process) {
                $processName = $process.ProcessName
                Write-Host "  Killing $processName (PID: $processId) on port $port..." -ForegroundColor Yellow
                Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
                $processesKilled++
                Write-Host "  ✓ Stopped" -ForegroundColor Green
            }
        }
    } catch {
        # Port not in use, skip
    }
}

Write-Host ""
if ($processesKilled -gt 0) {
    Write-Host "✓ Stopped $processesKilled process(es)" -ForegroundColor Green
} else {
    Write-Host "ℹ No Sheratan processes found running" -ForegroundColor Cyan
}

Write-Host ""
Write-Host "All services stopped." -ForegroundColor Gray
