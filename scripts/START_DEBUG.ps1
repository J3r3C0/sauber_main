# ============================================================================
# Sheratan - Simple Start (Single Window Debug Mode)
# ============================================================================
# Starts Core API only for debugging

$ErrorActionPreference = "Continue"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host ""
Write-Host "SHERATAN - DEBUG MODE (Core API Only)" -ForegroundColor Cyan
Write-Host ""

$PROJECT_ROOT = Resolve-Path (Join-Path $PSScriptRoot "..")

# Stop previous instances
Write-Host "Stopping previous instances..." -ForegroundColor Yellow
Get-Process | Where-Object { $_.ProcessName -eq "python" } | Stop-Process -Force -ErrorAction SilentlyContinue
Get-Process | Where-Object { $_.ProcessName -eq "node" } | Stop-Process -Force -ErrorAction SilentlyContinue

Write-Host ""
Write-Host "Starting Core API on http://localhost:8001..." -ForegroundColor Green
Write-Host ""

Set-Location (Join-Path $PROJECT_ROOT "core")
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --reload
