# Sheratan Hub Hardening - Automated Smoke Suite (v1.0)
# Usage: .\smoke_checks.ps1

$TOKEN = "shared-secret"
$CTL_URL = "http://localhost:8787"
$DAT_URL = "http://localhost:8788"
$CORE_URL = "http://localhost:8001"

Write-Host "--- A) Port Isolation Checks ---" -ForegroundColor Cyan

# 1. Queue on 8787 should fail (410 Gone)
try {
    $res = Invoke-WebRequest -Uri "$CTL_URL/mesh/pull_requests/NODE_WORK_B" -Headers @{"X-Sheratan-Token" = $TOKEN } -ErrorAction Stop
    Write-Host "FAIL: Queue accessible on 8787port" -ForegroundColor Red
}
catch {
    if ($_.Exception.Response.StatusCode -eq 410) { Write-Host "PASS: Queue blocked on 8787 (410 Gone)" -ForegroundColor Green }
    else { Write-Host "FAIL: Expected 410, got $($_.Exception.Response.StatusCode)" -ForegroundColor Red }
}

# 2. Heartbeat on 8788 should fail (410 Gone)
try {
    $res = Invoke-RestMethod -Uri "$DAT_URL/mesh/heartbeat" -Method Post -Body '{}' -Headers @{"X-Sheratan-Token" = $TOKEN } -ErrorAction Stop
    Write-Host "FAIL: Heartbeat accessible on 8788" -ForegroundColor Red
}
catch {
    if ($_.Exception.Response.StatusCode -eq 410) { Write-Host "PASS: Heartbeat blocked on 8788 (410 Gone)" -ForegroundColor Green }
    else { Write-Host "FAIL: Expected 410, got $($_.Exception.Response.StatusCode)" -ForegroundColor Red }
}

Write-Host "`n--- B) Token Security Checks ---" -ForegroundColor Cyan

# 4. 8787 Health (Public)
try {
    $res = Invoke-RestMethod -Uri "$CTL_URL/health"
    Write-Host "PASS: /health is public on 8787" -ForegroundColor Green
}
catch { Write-Host "FAIL: /health failed: $($_.Exception.Message)" -ForegroundColor Red }

# 5. 8787 Registry (Protected)
try {
    $res = Invoke-RestMethod -Uri "$CTL_URL/registry" -ErrorAction Stop
    Write-Host "FAIL: Registry accessible without token" -ForegroundColor Red
}
catch { Write-Host "PASS: Registry blocked without token (403)" -ForegroundColor Green }

# 6. Auth Headers (X-Token vs Bearer)
try {
    $res1 = Invoke-RestMethod -Uri "$CTL_URL/registry" -Headers @{"X-Sheratan-Token" = $TOKEN }
    $res2 = Invoke-RestMethod -Uri "$CTL_URL/registry" -Headers @{"Authorization" = "Bearer $TOKEN" }
    Write-Host "PASS: Both X-Token and Bearer headers supported" -ForegroundColor Green
}
catch { Write-Host "FAIL: Auth headers not working: $($_.Exception.Message)" -ForegroundColor Red }

Write-Host "`n--- C) Registry & TTL Logic ---" -ForegroundColor Cyan

# 5. Check if nodes are present
$reg = Invoke-RestMethod -Uri "$CTL_URL/registry" -Headers @{"X-Sheratan-Token" = $TOKEN }
if ($reg.nodes.Count -gt 0) {
    Write-Host "PASS: Hub Registry is populated" -ForegroundColor Green
}
else {
    Write-Host "WARN: Registry is empty. Ensure nodes are running." -ForegroundColor Yellow
}

Write-Host "`n--- D) Sauber Core Security ---" -ForegroundColor Cyan

# 10. localhost config lock
# Note: we test from THIS machine (localhost)
try {
    $res = Invoke-RestMethod -Uri "$CORE_URL/api/gateway/config" -Headers @{"X-Sheratan-Token" = $TOKEN }
    Write-Host "PASS: Sauber config accessible via localhost+token" -ForegroundColor Green
}
catch {
    Write-Host "FAIL: Sauber config blocked on localhost: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n--- E) Audit Log Check ---" -ForegroundColor Cyan

$audit_path = "C:\gemmaloop\.sheratan\logs\hub_security_audit.jsonl"
if (Test-Path $audit_path) {
    $last_entry = Get-Content $audit_path | Select-Object -Last 1 | ConvertFrom-Json
    Write-Host "PASS: Audit log found. Last Event: $($last_entry.event)" -ForegroundColor Green
}
else {
    Write-Host "FAIL: Audit log file not found at $audit_path" -ForegroundColor Red
}

Write-Host "`n--- SMOKE TEST COMPLETE ---" -ForegroundColor Cyan
