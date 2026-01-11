# Sheratan Clean Build - Verification Script
# ============================================================================
# Checks all services are responding correctly

$ErrorActionPreference = "Continue"

Write-Host ""
Write-Host "SHERATAN CLEAN BUILD - VERIFICATION" -ForegroundColor Cyan
Write-Host ""

$endpoints = @(
    @{Name = "Core API "; Url = "http://localhost:8001/api/status"; Required = $true },
    @{Name = "Broker   "; Url = "http://127.0.0.1:9000/status"; Required = $true },
    @{Name = "Host-A   "; Url = "http://127.0.0.1:8081/announce"; Required = $true },
    @{Name = "Host-B   "; Url = "http://127.0.0.1:8082/announce"; Required = $true },
    @{Name = "WebRelay "; Url = "http://localhost:3000/health"; Required = $true },
    @{Name = "Dashboard"; Url = "http://localhost:3001"; Required = $false }
)

$passed = 0
$failed = 0

foreach ($ep in $endpoints) {
    try {
        $res = Invoke-WebRequest -Uri $ep.Url -Method GET -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
        Write-Host "  [PASS] $($ep.Name) online" -ForegroundColor Green
        $passed++
    }
    catch {
        if ($ep.Required) {
            Write-Host "  [FAIL] $($ep.Name) OFFLINE (Required)" -ForegroundColor Red
            $failed++
        }
        else {
            Write-Host "  [WARN] $($ep.Name) not responding (Optional)" -ForegroundColor Yellow
        }
    }
}

Write-Host ""
Write-Host "Results: $passed passed, $failed failed" -ForegroundColor $(if ($failed -eq 0) { "Green" } else { "Yellow" })

if ($failed -eq 0) {
    Write-Host ""
    Write-Host "[OK] All required services are online!" -ForegroundColor Green
    Write-Host ""
    exit 0
}
else {
    Write-Host ""
    Write-Host "[WARN] Some services are not responding. Check individual terminal windows." -ForegroundColor Yellow
    Write-Host ""
    exit 1
}
