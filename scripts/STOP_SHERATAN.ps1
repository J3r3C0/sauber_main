# ============================================================================
# Sheratan - Master Stop Script
# ============================================================================
# Terminates all Sheratan processes (PowerShell, Python, Uvicorn, Node).

Write-Host ""
Write-Host "🛑 Stopping Sheratan System..." -ForegroundColor Yellow

# Kill Python processes (Hosts, Broker, Core background tasks)
Write-Host "  > Killing Python processes..." -ForegroundColor Gray
Get-Process | Where-Object { $_.ProcessName -eq "python" } | Stop-Process -Force -ErrorAction SilentlyContinue

# Kill Uvicorn (Core)
Write-Host "  > Killing Uvicorn..." -ForegroundColor Gray
Get-Process | Where-Object { $_.ProcessName -eq "uvicorn" } | Stop-Process -Force -ErrorAction SilentlyContinue

# Kill Node (WebRelay)
Write-Host "  > Killing Node.js processes..." -ForegroundColor Gray
Get-Process | Where-Object { $_.ProcessName -eq "node" } | Stop-Process -Force -ErrorAction SilentlyContinue

# Kill Chrome (if started by Sheratan)
Write-Host "  > Optional: Killing Chrome..." -ForegroundColor Gray
# Get-Process chrome | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host "✅ System stopped." -ForegroundColor Green
Write-Host ""
