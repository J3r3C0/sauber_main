# ============================================================================
# Sheratan Clean Build - System Reset Script
# ============================================================================
# Cleans job queues, logs, and temporary files for a fresh start

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "SHERATAN CLEAN BUILD - SYSTEM RESET" -ForegroundColor Yellow
Write-Host ""

$PROJECT_ROOT = Resolve-Path (Join-Path $PSScriptRoot "..")

# Stop all Sheratan processes
Write-Host "[1/3] Stopping all Sheratan processes..." -ForegroundColor Yellow
$sh_procs = @("python", "node", "chrome", "pwsh")
foreach ($proc in $sh_procs) {
    Get-Process -Name $proc -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle -like "SHERATAN:*" } | ForEach-Object {
        Write-Host "  - Stopping $($_.ProcessName) (Id: $($_.Id))" -ForegroundColor Gray
        Stop-Process -Id $_.Id -Force -ErrorAction SilentlyContinue
    }
}
Start-Sleep -Seconds 2
Write-Host "  [OK] All processes stopped" -ForegroundColor Green

# Clean runtime directories
Write-Host ""
Write-Host "[2/3] Cleaning runtime directories..." -ForegroundColor Yellow
$dirs = @(
    "mesh\runtime\inbox",
    "mesh\runtime\queue\approved",
    "mesh\runtime\queue\blocked",
    "mesh\runtime\outbox\results",
    "mesh\runtime\logs"
)

foreach ($d in $dirs) {
    $p = Join-Path $PROJECT_ROOT $d
    if (Test-Path $p) {
        Get-ChildItem -Path $p -File | Remove-Item -Force
        Write-Host "  - Cleaned $d" -ForegroundColor Gray
    }
}

# Reset ledger
$ledger = Join-Path $PROJECT_ROOT "mesh\runtime\outbox\ledger.jsonl"
if (Test-Path $ledger) {
    Clear-Content -Path $ledger
    Write-Host "  - Reset ledger" -ForegroundColor Gray
}

Write-Host "  [OK] Runtime cleaned" -ForegroundColor Green

# Clean Core data (if exists)
Write-Host ""
Write-Host "[3/3] Cleaning Core data..." -ForegroundColor Yellow
$coreData = Join-Path $PROJECT_ROOT "core\data"
if (Test-Path $coreData) {
    Get-ChildItem -Path $coreData -Recurse -File | Remove-Item -Force
    Write-Host "  - Cleaned core/data" -ForegroundColor Gray
}
Write-Host "  [OK] Core data cleaned" -ForegroundColor Green

Write-Host ""
Write-Host "[OK] SYSTEM RESET COMPLETE" -ForegroundColor Green
Write-Host " You can now run START.ps1 for a fresh start."
Write-Host ""
