# verify_a2_attestation.ps1
$ErrorActionPreference = "Stop"

$CoreUrl = "http://localhost:8001"
$Endpoint = "$CoreUrl/api/hosts/heartbeat"
$NodeId = "test-node-A2"

function Send-Heartbeat($Payload) {
    Write-Host "`nSending Heartbeat for node: $($Payload.host_id)" -ForegroundColor Cyan
    $Response = Invoke-RestMethod -Uri $Endpoint -Method Post -Body ($Payload | ConvertTo-Json) -ContentType "application/json"
    return $Response
}

Write-Host "=== Track A2: Node Attestation Verification ===" -ForegroundColor Yellow

# T1: First Seen => OK
$T1_Payload = @{
    host_id     = $NodeId
    status      = "online"
    attestation = @{
        build_id        = "v1.0.0"
        capability_hash = "hash-A"
        runtime         = @{ os = "windows"; arch = "x64" }
    }
}
$Res1 = Send-Heartbeat $T1_Payload
if ($Res1.attestation_status -eq "OK") {
    Write-Host "[PASS] T1: First Seen is OK" -ForegroundColor Green
}
else {
    Write-Host "[FAIL] T1: Expected OK, got $($Res1.attestation_status)" -ForegroundColor Red
}

# T2: Drift => DRIFT (Change build_id)
$T2_Payload = @{
    host_id     = $NodeId
    status      = "online"
    attestation = @{
        build_id        = "v1.1.0-drifted"
        capability_hash = "hash-A"
        runtime         = @{ os = "windows"; arch = "x64" }
    }
}
$Res2 = Send-Heartbeat $T2_Payload
if ($Res2.attestation_status -eq "DRIFT") {
    Write-Host "[PASS] T2: Drift detected" -ForegroundColor Green
}
else {
    Write-Host "[FAIL] T2: Expected DRIFT, got $($Res2.attestation_status)" -ForegroundColor Red
}

# T3: Spoof Detection (Flip-Flop)
# Threshold is 3 changes. We already had one change (T1 -> T2 content-wise, actually T2 was drift).
# Let's send 3 more changes in rapid succession.

$Hashes = @("hash-B", "hash-C", "hash-D")
foreach ($h in $Hashes) {
    $TP = @{
        host_id     = $NodeId
        status      = "online"
        attestation = @{
            build_id        = "v1.1.0-drifted"
            capability_hash = $h
            runtime         = @{ os = "windows"; arch = "x64" }
        }
    }
    $Res = Send-Heartbeat $TP
    Write-Host "Current status: $($Res.attestation_status)"
}

if ($Res.attestation_status -eq "SPOOF_SUSPECT") {
    Write-Host "[PASS] T3: Spoof Suspect detected" -ForegroundColor Green
}
else {
    Write-Host "[FAIL] T3: Expected SPOOF_SUSPECT, got $($Res.attestation_status)" -ForegroundColor Red
}

# T4: Missing => MISSING (No attestation block)
$NodeId_New = "test-node-missing"
$T4_Payload = @{
    host_id = $NodeId_New
    status  = "online"
}
$Res4 = Send-Heartbeat $T4_Payload
if ($Res4.attestation_status -eq "MISSING") {
    Write-Host "[PASS] T4: Missing attestation handled" -ForegroundColor Green
}
else {
    Write-Host "[FAIL] T4: Expected MISSING, got $($Res4.attestation_status)" -ForegroundColor Red
}

Write-Host "`n=== Verification Complete ===" -ForegroundColor Yellow
