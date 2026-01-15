# verify_a1_token_rotation.ps1
# Manual verification for Track A1 (Token Rotation)

$ErrorActionPreference = "Stop"
$BaseUrl = "http://localhost:8787"

function Invoke-HealthCheck($token) {
    try {
        $res = Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get -Headers @{"X-Sheratan-Token" = $token }
        return "OK"
    }
    catch {
        return "FAIL ($($_.Exception.Response.StatusCode))"
    }
}

function Kill-Hub {
    # Aggressive kill for all python processes to ensure children are gone
    Stop-Process -Name python -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3
}

Write-Host "== Track A1 Manual Verification (Token Rotation) ==" -ForegroundColor Cyan
Kill-Hub

# Scenario 1: Legacy Compatibility
Write-Host "`n--- Scenario 1: Legacy Token ---" -ForegroundColor Yellow
$legacy_proc = Start-Process python -ArgumentList "-m", "hub.serve_gateway", "--port-control", "8787", "--port-data", "8788" -PassThru -NoNewWindow -Environment @{
    "PYTHONPATH"                  = "C:\gemmaloop\repo_sync_v1";
    "SHERATAN_HUB_TOKEN"          = "legacy-secret";
    "SHERATAN_HUB_TOKEN_REQUIRED" = "1"
}
Start-Sleep -Seconds 5
$r1 = Invoke-HealthCheck "legacy-secret"
Write-Host "Legacy Auth: $r1"
Kill-Hub

# Scenario 2: Active/Next Window
Write-Host "`n--- Scenario 2: Dual Token Window ---" -ForegroundColor Yellow
$future = (Get-Date).ToUniversalTime().AddMinutes(5).ToString("yyyy-MM-ddTHH:mm:ssZ")
$dual_proc = Start-Process python -ArgumentList "-m", "hub.serve_gateway", "--port-control", "8787", "--port-data", "8788" -PassThru -NoNewWindow -Environment @{
    "PYTHONPATH"                        = "C:\gemmaloop\repo_sync_v1";
    "SHERATAN_HUB_TOKEN_ACTIVE"         = "v1-active";
    "SHERATAN_HUB_TOKEN_NEXT"           = "v2-next";
    "SHERATAN_HUB_TOKEN_ROTATION_UNTIL" = $future;
    "SHERATAN_HUB_TOKEN_REQUIRED"       = "1"
}
Start-Sleep -Seconds 5
$r2a = Invoke-HealthCheck "v1-active"
$r2b = Invoke-HealthCheck "v2-next"
Write-Host "Active Token: $r2a"
Write-Host "Next Token (Before Deadline): $r2b"
Kill-Hub

# Scenario 3: Retirement after Deadline
Write-Host "`n--- Scenario 3: Retirement & Promotion ---" -ForegroundColor Yellow
$past = (Get-Date).ToUniversalTime().AddMinutes(-5).ToString("yyyy-MM-ddTHH:mm:ssZ")
$retire_proc = Start-Process python -ArgumentList "-m", "hub.serve_gateway", "--port-control", "8787", "--port-data", "8788" -PassThru -NoNewWindow -Environment @{
    "PYTHONPATH"                        = "C:\gemmaloop\repo_sync_v1";
    "SHERATAN_HUB_TOKEN_ACTIVE"         = "v1-old";
    "SHERATAN_HUB_TOKEN_NEXT"           = "v2-new";
    "SHERATAN_HUB_TOKEN_ROTATION_UNTIL" = $past;
    "SHERATAN_HUB_TOKEN_REQUIRED"       = "1"
}
Start-Sleep -Seconds 5
$r3a = Invoke-HealthCheck "v1-old"
$r3b = Invoke-HealthCheck "v2-new"
Write-Host "Old Token (After Deadline): $r3a"
Write-Host "New Token (After Promotion): $r3b"
Kill-Hub

Write-Host "`nALL DONE: Track A1 manual verification finished." -ForegroundColor Cyan
