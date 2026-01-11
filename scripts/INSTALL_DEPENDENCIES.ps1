# ============================================================================
# Sheratan Clean Build - Install Dependencies
# ============================================================================
# Installs all Python and Node.js dependencies

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "SHERATAN CLEAN BUILD - DEPENDENCY INSTALLATION" -ForegroundColor Cyan
Write-Host ""

$PROJECT_ROOT = Resolve-Path (Join-Path $PSScriptRoot "..")

# --- 1) Python Dependencies ---
Write-Host "[1/5] Installing Python dependencies for Core..." -ForegroundColor Yellow
$coreReq = Join-Path $PROJECT_ROOT "core\requirements.txt"
if (Test-Path $coreReq) {
    Set-Location (Join-Path $PROJECT_ROOT "core")
    pip install -r requirements.txt
    Write-Host "  [OK] Core dependencies installed" -ForegroundColor Green
}
else {
    Write-Host "  [WARN] core/requirements.txt not found" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[2/5] Installing Python dependencies for Worker..." -ForegroundColor Yellow
$workerReq = Join-Path $PROJECT_ROOT "worker\requirements.txt"
if (Test-Path $workerReq) {
    Set-Location (Join-Path $PROJECT_ROOT "worker")
    pip install -r requirements.txt
    Write-Host "  [OK] Worker dependencies installed" -ForegroundColor Green
}
else {
    Write-Host "  [WARN] worker/requirements.txt not found" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[3/5] Installing Python dependencies for Mesh..." -ForegroundColor Yellow
$meshReq = Join-Path $PROJECT_ROOT "mesh\offgrid\requirements.txt"
if (Test-Path $meshReq) {
    Set-Location (Join-Path $PROJECT_ROOT "mesh\offgrid")
    pip install -r requirements.txt
    Write-Host "  [OK] Mesh dependencies installed" -ForegroundColor Green
}
else {
    Write-Host "  [WARN] mesh/offgrid/requirements.txt not found" -ForegroundColor Yellow
}

# --- 2) Node.js Dependencies ---
Write-Host ""
Write-Host "[4/5] Installing Node.js dependencies for Dashboard..." -ForegroundColor Yellow
$dashboardPkg = Join-Path $PROJECT_ROOT "dashboard\package.json"
if (Test-Path $dashboardPkg) {
    Set-Location (Join-Path $PROJECT_ROOT "dashboard")
    npm install
    Write-Host "  [OK] Dashboard dependencies installed" -ForegroundColor Green
}
else {
    Write-Host "  [WARN] dashboard/package.json not found" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[5/5] Installing Node.js dependencies for WebRelay..." -ForegroundColor Yellow
$webrelayPkg = Join-Path $PROJECT_ROOT "external\webrelay\package.json"
if (Test-Path $webrelayPkg) {
    Set-Location (Join-Path $PROJECT_ROOT "external\webrelay")
    npm install
    Write-Host "  [OK] WebRelay dependencies installed" -ForegroundColor Green
}
else {
    Write-Host "  [WARN] external/webrelay/package.json not found" -ForegroundColor Yellow
}

# --- 3) Build WebRelay TypeScript ---
Write-Host ""
Write-Host "Building WebRelay TypeScript..." -ForegroundColor Yellow
if (Test-Path $webrelayPkg) {
    Set-Location (Join-Path $PROJECT_ROOT "external\webrelay")
    npm run build
    Write-Host "  [OK] WebRelay built successfully" -ForegroundColor Green
}

Set-Location $PROJECT_ROOT

Write-Host ""
Write-Host "[OK] DEPENDENCY INSTALLATION COMPLETE" -ForegroundColor Green
Write-Host " You can now run .\START.ps1 to start the system."
Write-Host ""
