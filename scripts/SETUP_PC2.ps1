# ============================================================================
# Sheratan PC2 Setup Script
# Automated setup for burn-in testing on secondary machine
# ============================================================================

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "SHERATAN PC2 SETUP - BURN-IN TEST ENVIRONMENT" -ForegroundColor Cyan
Write-Host ""

# Configuration
$REPO_URL = "https://github.com/YOUR_USERNAME/sauber_main.git"  # UPDATE THIS
$INSTALL_DIR = "C:\sheratan_test"
$PC1_IP = "192.168.1.XXX"  # UPDATE THIS with PC1 IP

# Step 1: Clone Repository
Write-Host "[1/6] Cloning Sheratan repository..." -ForegroundColor Yellow
if (Test-Path $INSTALL_DIR) {
    Write-Host "  Directory exists. Pulling latest changes..." -ForegroundColor Gray
    Set-Location $INSTALL_DIR
    git pull
}
else {
    git clone $REPO_URL $INSTALL_DIR
    Set-Location $INSTALL_DIR
}
Write-Host "  [OK] Repository ready" -ForegroundColor Green

# Step 2: Install Python Dependencies
Write-Host ""
Write-Host "[2/6] Installing Python dependencies..." -ForegroundColor Yellow
.\scripts\INSTALL_DEPENDENCIES.ps1
Write-Host "  [OK] Dependencies installed" -ForegroundColor Green

# Step 3: Configure for PC2
Write-Host ""
Write-Host "[3/6] Configuring for PC2..." -ForegroundColor Yellow

# Create .env from .env.example if it doesn't exist
$envExample = Join-Path $INSTALL_DIR "external\dashboard\.env.example"
$envFile = Join-Path $INSTALL_DIR "external\dashboard\.env"
if (-not (Test-Path $envFile)) {
    if (Test-Path $envExample) {
        Copy-Item $envExample $envFile
        Write-Host "  Created .env from .env.example" -ForegroundColor Gray
    }
    else {
        Write-Host "  [WARN] .env.example not found, creating default .env" -ForegroundColor Yellow
        @"
VITE_API_BASE_URL=http://localhost:8001
VITE_BACKEND_POC_URL=http://localhost:7007
"@ | Out-File -FilePath $envFile -Encoding UTF8
    }
}

Write-Host "  [OK] Configuration complete" -ForegroundColor Green

# Step 4: Verify Chrome Installation
Write-Host ""
Write-Host "[4/6] Verifying Chrome installation..." -ForegroundColor Yellow
.\scripts\find_chrome.bat
if ($LASTEXITCODE -ne 0) {
    Write-Host "  [ERROR] Chrome not found. Please install Chrome." -ForegroundColor Red
    exit 1
}
Write-Host "  [OK] Chrome found" -ForegroundColor Green

# Step 5: Create Burn-In Test Directories
Write-Host ""
Write-Host "[5/6] Creating test directories..." -ForegroundColor Yellow
$testDirs = @("logs\burn_in", "data\burn_in_results", "runtime")
foreach ($dir in $testDirs) {
    if (-not (Test-Path $dir)) {
        New-Item -ItemType Directory -Path $dir -Force | Out-Null
    }
}
Write-Host "  [OK] Test directories created" -ForegroundColor Green

# Step 6: Network Configuration Info
Write-Host ""
Write-Host "[6/6] Network configuration..." -ForegroundColor Yellow
$PC2_IP = (Get-NetIPAddress -AddressFamily IPv4 | Where-Object { $_.InterfaceAlias -notlike "*Loopback*" } | Select-Object -First 1).IPAddress
Write-Host "  PC2 IP Address: $PC2_IP" -ForegroundColor Cyan
Write-Host "  PC1 IP Address: $PC1_IP (configured)" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Dashboard will be accessible at: http://${PC2_IP}:3001" -ForegroundColor Cyan
Write-Host "  Core API will be accessible at: http://${PC2_IP}:8001" -ForegroundColor Cyan
Write-Host ""

# Summary
Write-Host ""
Write-Host "============================================" -ForegroundColor Green
Write-Host "SETUP COMPLETE!" -ForegroundColor Green
Write-Host "============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "  1. Start the system: .\START_COMPLETE_SYSTEM.bat"
Write-Host "  2. Run burn-in tests: .\tests\burn_in\RUN_ALL_TESTS.ps1"
Write-Host "  3. Monitor from PC1: http://${PC2_IP}:3001"
Write-Host ""
Write-Host "Burn-in test results will be saved to: data\burn_in_results\" -ForegroundColor Gray
Write-Host ""

pause
