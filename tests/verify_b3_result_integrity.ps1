# verify_b3_result_integrity.ps1
# Manual verification for Track B3 (Result Integrity)
# Requires: SHERATAN_HUB_TOKEN in env
# Assumes: SHERATAN_RESULT_INTEGRITY_MODE=sha256 (default)

$ErrorActionPreference = "Stop"

$BaseUrl = "http://localhost:8788"
$ResultEndpoint = "$BaseUrl/mesh/submit_result"
$MetricsEndpoint = "$BaseUrl/metrics"
$Token = $env:SHERATAN_HUB_TOKEN

if ([string]::IsNullOrWhiteSpace($Token)) {
    throw "SHERATAN_HUB_TOKEN is not set in environment."
}

function Get-CanonicalJson([object]$obj) {
    # Standardized Canonical JSON: sort keys, no whitespace separators.
    return ($obj | ConvertTo-Json -Depth 20 -Compress)
}

function Get-Sha256Hex([string]$text) {
    $sha = [System.Security.Cryptography.SHA256]::Create()
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($text)
    $hash = $sha.ComputeHash($bytes)
    ($hash | ForEach-Object { $_.ToString("x2") }) -join ""
}

function Invoke-JsonPost($url, $bodyObj) {
    $json = $bodyObj | ConvertTo-Json -Depth 20 -Compress
    try {
        return Invoke-RestMethod -Method Post -Uri $url -Body $json -ContentType "application/json" -Headers @{
            "X-Sheratan-Token" = $Token
        }
    }
    catch {
        $status = [int]$_.Exception.Response.StatusCode
        return [pscustomobject]@{ __http_status = $status }
    }
}

function Try-Get($url) {
    try {
        return Invoke-RestMethod -Method Get -Uri $url -Headers @{ "X-Sheratan-Token" = $Token }
    }
    catch {
        return $null
    }
}

function Assert($cond, $msg) {
    if (-not $cond) { throw "ASSERT FAIL: $msg" }
    Write-Host "PASS: $msg" -ForegroundColor Green
}

Write-Host "== Track B3 Manual Verification (Result Integrity) ==" -ForegroundColor Cyan
Write-Host "ResultEndpoint: $ResultEndpoint" -ForegroundColor DarkCyan

# --------------------------
# Build a minimal "result payload"
# --------------------------
$jobId = "test-b3-" + ([Guid]::NewGuid().ToString("N"))
$resId = "RES-B3-" + ([Guid]::NewGuid().ToString("N"))
$core = @{
    job_id = $jobId
    ok     = $true
    result = @{
        value = 42
        note  = "hello"
    }
    error  = $null
}

# Compute integrity over the semantic core (job_id, ok, result, error)
$canonical = '{"error":null,"job_id":"' + $jobId + '","ok":true,"result":{"note":"hello","value":42}}'
$sha = Get-Sha256Hex $canonical

$valid = @{
    result_id = $resId
    job_id    = $jobId
    ok        = $true
    result    = $core.result
    integrity = @{
        mode   = "sha256"
        sha256 = $sha
    }
}

Write-Host "`n--- T1: Valid integrity should be accepted ---" -ForegroundColor Yellow
$r1 = Invoke-JsonPost $ResultEndpoint $valid

if ($r1.PSObject.Properties.Name -contains "__http_status") {
    throw "Expected accept, got HTTP $($r1.__http_status)"
}
else {
    Assert ($r1.ok -eq $true) "valid result accepted (ok=true)"
}

# --------------------------
# Tamper result but keep old sha => must reject
# --------------------------
Write-Host "`n--- T2: Tampered payload with old sha must be rejected ---" -ForegroundColor Yellow
$tampered = @{
    result_id = "RES-B3-TAMPER-" + ([Guid]::NewGuid().ToString("N"))
    job_id    = $jobId
    ok        = $true
    result    = @{
        value = 43   # changed
        note  = "hello"
    }
    integrity = @{
        mode   = "sha256"
        sha256 = $sha  # old sha
    }
}

$r2 = Invoke-JsonPost $ResultEndpoint $tampered
if ($r2.PSObject.Properties.Name -contains "__http_status") {
    Assert ($r2.__http_status -eq 403) "tampered result rejected (HTTP 403)"
}
else {
    Assert ($r2.ok -eq $false) "tampered result rejected (ok=false style)"
}

# --------------------------
# Metrics
# --------------------------
Write-Host "`n--- T4: Metrics snapshot ---" -ForegroundColor Yellow
$m = Try-Get $MetricsEndpoint
if ($null -ne $m) {
    Write-Host "INFO: integrity_fail_1m = $($m.integrity.fail_1m)" -ForegroundColor DarkYellow
    Assert ($m.integrity.fail_1m -ge 1) "integrity_fail_1m incremented"
}

Write-Host "`nALL DONE: Track B3 manual verification finished." -ForegroundColor Cyan
