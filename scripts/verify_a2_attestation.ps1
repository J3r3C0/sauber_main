# verify_a2_attestation.ps1
# Manual verification for Track A2 (Node Attestation)

$ErrorActionPreference = "Stop"
$BaseUrl = "http://localhost:8787"
$Token = $env:SHERATAN_HUB_TOKEN

if ([string]::IsNullOrWhiteSpace($Token)) {
    throw "SHERATAN_HUB_TOKEN is not set."
}

function Invoke-Heartbeat($payload) {
    return Invoke-RestMethod -Uri "$BaseUrl/mesh/heartbeat" -Method Post -Body ($payload | ConvertTo-Json -Depth 20 -Compress) -ContentType "application/json" -Headers @{"X-Sheratan-Token" = $Token }
}

function Get-Registry() {
    return Invoke-RestMethod -Uri "$BaseUrl/registry" -Method Get -Headers @{"X-Sheratan-Token" = $Token }
}

function Assert-Status($node_id, $expected_status, $msg) {
    $reg = Get-Registry
    $node = $reg.nodes.$node_id
    if ($node.attestation.status -eq $expected_status) {
        Write-Host "PASS: $msg (Status: $expected_status)" -ForegroundColor Green
    }
    else {
        Write-Host "FAIL: $msg (Expected: $expected_status, Got: $($node.attestation.status))" -ForegroundColor Red
        throw "Assertion failed"
    }
}

Write-Host "== Track A2 Manual Verification (Node Attestation) ==" -ForegroundColor Cyan

$nodeId = "verify-a2-" + [Guid]::NewGuid().ToString("N").Substring(0, 8)

# 1. First Seen
Write-Host "`n--- T1: First Seen Registration ---" -ForegroundColor Yellow
$hb1 = @{
    node_id     = $nodeId
    health      = "GREEN"
    attestation = @{
        build_id        = "v1.0"
        capability_hash = "hash-A"
        runtime         = @{ os = "windows" }
    }
}
Invoke-Heartbeat $hb1 | Out-Null
Assert-Status $nodeId "OK" "Node registered with OK status"

# 2. Drift Detection
Write-Host "`n--- T2: Drift Detection ---" -ForegroundColor Yellow
$hb2 = @{
    node_id     = $nodeId
    health      = "GREEN"
    attestation = @{
        build_id        = "v1.1" # Changed build
        capability_hash = "hash-A"
    }
}
Invoke-Heartbeat $hb2 | Out-Null
Assert-Status $nodeId "DRIFT" "Node detected as DRIFT (Health should be YELLOW)"

$reg = Get-Registry
if ($reg.nodes.$nodeId.health -eq "YELLOW") {
    Write-Host "PASS: Node health is YELLOW" -ForegroundColor Green
}
else {
    Write-Host "FAIL: Node health is $($reg.nodes.$nodeId.health)" -ForegroundColor Red
}

# 3. Spoof Detection (Flip-Flop)
Write-Host "`n--- T3: Spoof Detection (Flip-Flop) ---" -ForegroundColor Yellow
$hb3 = @{
    node_id     = $nodeId
    attestation = @{ build_id = "v1.1"; capability_hash = "hash-B" }
}
$hb4 = @{
    node_id     = $nodeId
    attestation = @{ build_id = "v1.1"; capability_hash = "hash-C" }
}
$hb5 = @{
    node_id     = $nodeId
    attestation = @{ build_id = "v1.1"; capability_hash = "hash-D" }
}

Write-Host "Triggering flips..."
Invoke-Heartbeat $hb3 | Out-Null
Invoke-Heartbeat $hb4 | Out-Null
Invoke-Heartbeat $hb5 | Out-Null # Should cross threshold of 3 (A->B, B->C, C->D)

Assert-Status $nodeId "SPOOF_SUSPECT" "Node detected as SPOOF_SUSPECT"

Write-Host "`nALL DONE: Track A2 manual verification finished." -ForegroundColor Cyan
