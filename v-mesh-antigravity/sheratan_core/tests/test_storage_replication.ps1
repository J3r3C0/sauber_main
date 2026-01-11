# test_storage_replication.ps1
# Verifies that Mission creation in Core is replicated to Offgrid Memory

Write-Host "=== Storage Replication Test ===" -ForegroundColor Cyan

# 1. Create Mission via Core API
Write-Host "Creating Mission via Core..." -ForegroundColor Yellow
$mission_payload = @{
    title = "Storage Replication Test"
    description = "Verifying async replication to Offgrid memory"
    metadata = @{ test_id = "storage-sync-$(Get-Date -Format 'yyyyMMdd-HHmm')" }
    tags = @("test", "replication")
} | ConvertTo-Json

$resp = Invoke-WebRequest -Uri "http://localhost:8001/api/missions" `
    -Method POST `
    -ContentType "application/json" `
    -Body $mission_payload

$mission = $resp.Content | ConvertFrom-Json
$mission_id = $mission.id
Write-Host "✓ Mission Created: $mission_id" -ForegroundColor Green

# 2. Wait for async replication
Write-Host "Waiting for replication (2s)..."
Start-Sleep -Seconds 2

# 3. Check memory on Host-A
Write-Host "Checking Memory on Host-A (Port 8081)..." -ForegroundColor Yellow
try {
    $query_resp = Invoke-WebRequest -Uri "http://127.0.0.1:8081/memory/query?limit=10" -Method GET
    $events = $query_resp.Content | ConvertFrom-Json
    
    $found = $false
    foreach ($event in $events.events) {
        if ($event.meta.key -eq "mission:$mission_id") {
            Write-Host "✓ SUCCESS! Mission found in Offgrid Memory (eid: $($event.eid))" -ForegroundColor Green
            $found = $true
            break
        }
    }
    
    if (-not $found) {
        Write-Host "✗ Mission NOT found in memory query." -ForegroundColor Red
        Write-Host "Checking Host-B..."
        $query_resp_b = Invoke-WebRequest -Uri "http://127.0.0.1:8082/memory/query?limit=10" -Method GET
        $events_b = $query_resp_b.Content | ConvertFrom-Json
        foreach ($event in $events_b.events) {
            if ($event.meta.key -eq "mission:$mission_id") {
                Write-Host "✓ SUCCESS! Mission found in Host-B Memory (eid: $($event.eid))" -ForegroundColor Green
                $found = $true
                break
            }
        }
    }
    
    if (-not $found) {
        Write-Host "Replication check FAILED." -ForegroundColor Red
        exit 1
    }
} catch {
    Write-Host "Error checking memory: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Done ===" -ForegroundColor Cyan
