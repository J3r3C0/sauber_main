# verify_b2_idempotency.ps1
#Hier ist ein B2 Manual Verification Script (PowerShell), das genau die drei Kernfälle prüft: Dedup Hit, Collision (409), Cached Completion.
#Ich schreibe es so, dass du es als c:\sauber_main\verify_b2_idempotency.ps1 ablegen kannst (oder einfach copy/paste im Terminal).

#Annahmen:

#Hub Data läuft auf http://localhost:8788

#Token liegt in $env:SHERATAN_HUB_TOKEN

#/mesh/submit_request existiert wie beschrieben

#Es gibt entweder bereits ein Result/Completion-Path, oder du kannst den “Completion-Teil” überspringen (Script markiert das als optional).
# Manual verification for Track B2 (Idempotency & Dedup)
# Requires: SHERATAN_HUB_TOKEN in env

$ErrorActionPreference = "Stop"

$BaseUrl = "http://localhost:8788"
$Token = $env:SHERATAN_HUB_TOKEN

if ([string]::IsNullOrWhiteSpace($Token)) {
    throw "SHERATAN_HUB_TOKEN is not set in environment."
}

function Invoke-JsonPost($url, $bodyObj) {
    $json = $bodyObj | ConvertTo-Json -Depth 10
    try {
        return Invoke-RestMethod -Method Post -Uri $url -Body $json -ContentType "application/json" -Headers @{
            "X-Sheratan-Token" = $Token
        }
    }
    catch {
        # Surface HTTP status + body if present
        $resp = $_.Exception.Response
        if ($resp -and $resp.StatusCode) {
            $status = [int]$resp.StatusCode
            $reader = New-Object System.IO.StreamReader($resp.GetResponseStream())
            $body = $reader.ReadToEnd()
            return [pscustomobject]@{ __http_status = $status; __http_body = $body }
        }
        throw
    }
}

function Assert($cond, $msg) {
    if (-not $cond) { throw "ASSERT FAIL: $msg" }
    Write-Host "PASS: $msg" -ForegroundColor Green
}

Write-Host "== Track B2 Manual Verification ==" -ForegroundColor Cyan
Write-Host "Base: $BaseUrl" -ForegroundColor DarkCyan

# --------------------------
# Test 1: Dedup Hit (same key + same payload)
# --------------------------
Write-Host "`n--- T1: Dedup Hit (same key + same payload) ---" -ForegroundColor Yellow

$idKey = "test-b2-" + ([Guid]::NewGuid().ToString("N"))
$payload = @{
    idempotency_key = $idKey
    kind            = "echo_test"
    params          = @{ msg = "hello"; n = 1 }
}

$r1 = Invoke-JsonPost "$BaseUrl/mesh/submit_request" $payload
Assert ($r1.ok -eq $true) "first submit ok=true"
Assert (-not [string]::IsNullOrWhiteSpace($r1.request_id)) "first submit returns request_id"
Assert (-not [string]::IsNullOrWhiteSpace($r1.job_id)) "first submit returns job_id"
Assert (($r1.status -eq "accepted") -or ($r1.status -eq "in_progress")) "first submit status accepted/in_progress"
Assert (($r1.dedup -eq $false) -or ($null -eq $r1.dedup)) "first submit dedup=false (or omitted)"

$r2 = Invoke-JsonPost "$BaseUrl/mesh/submit_request" $payload
Assert ($r2.ok -eq $true) "second submit ok=true"
Assert ($r2.job_id -eq $r1.job_id) "second submit returns same job_id"
Assert ($r2.dedup -eq $true) "second submit dedup=true"
Assert (($r2.status -eq "in_progress") -or ($r2.status -eq "completed")) "second submit status in_progress/completed"

Write-Host "INFO: job_id=$($r1.job_id) key=$idKey" -ForegroundColor DarkGray

# --------------------------
# Test 2: Collision (same key + different payload) => 409
# --------------------------
Write-Host "`n--- T2: Collision (same key + different payload) ---" -ForegroundColor Yellow

$payload2 = @{
    idempotency_key = $idKey   # same key
    kind            = "echo_test"
    params          = @{ msg = "hello"; n = 2 } # different params => different payload hash
}

$r3 = Invoke-JsonPost "$BaseUrl/mesh/submit_request" $payload2

# If API returns structured error instead of throwing, we capture __http_status in object.
if ($r3.PSObject.Properties.Name -contains "__http_status") {
    Assert ($r3.__http_status -eq 409) "collision returns HTTP 409"
    Write-Host "INFO: collision body: $($r3.__http_body)" -ForegroundColor DarkGray
}
else {
    # Some APIs wrap errors inside ok=false with 200 (not preferred, but handle)
    Assert ($r3.ok -eq $false) "collision returns ok=false (non-HTTP error style)"
    Write-Host "INFO: collision response: $(($r3 | ConvertTo-Json -Depth 10))" -ForegroundColor DarkGray
}

# --------------------------
# Test 3: Cached Completion (optional)
# --------------------------
Write-Host "`n--- T3: Cached Completion (optional) ---" -ForegroundColor Yellow

Write-Host "NOTE: This requires a completion path that marks job_id as completed and updates idempotency store." -ForegroundColor DarkYellow
Write-Host "If you don't have a way to complete echo_test jobs, skip this section." -ForegroundColor DarkYellow

# If you have a known endpoint to sync/complete results, set it here.
# Example (adjust to your actual API):
# $CompleteUrl = "http://localhost:8001/api/jobs/$($r1.job_id)/sync"
# Or: "$BaseUrl/mesh/results/submit"
$CompleteUrl = $env:SHERATAN_TEST_COMPLETE_URL

if ([string]::IsNullOrWhiteSpace($CompleteUrl)) {
    Write-Host "SKIP: Set SHERATAN_TEST_COMPLETE_URL to enable completion test." -ForegroundColor DarkYellow
}
else {
    # Example completion payload - adjust as needed
    $completion = @{
        job_id = $r1.job_id
        ok     = $true
        result = @{ echoed = $payload.params; ts = (Get-Date).ToString("o") }
    }

    $c = Invoke-JsonPost $CompleteUrl $completion
    Write-Host "INFO: completion response: $(($c | ConvertTo-Json -Depth 10))" -ForegroundColor DarkGray

    # Re-submit original idempotent request -> should now be completed
    Start-Sleep -Milliseconds 200
    $r4 = Invoke-JsonPost "$BaseUrl/mesh/submit_request" $payload
    Assert ($r4.ok -eq $true) "post-completion submit ok=true"
    Assert ($r4.dedup -eq $true) "post-completion submit dedup=true"
    Assert ($r4.status -eq "completed") "post-completion submit status=completed"
    Write-Host "INFO: completed cached response: $(($r4 | ConvertTo-Json -Depth 10))" -ForegroundColor DarkGray
}

Write-Host "`nALL DONE: Track B2 manual verification finished." -ForegroundColor Cyan
