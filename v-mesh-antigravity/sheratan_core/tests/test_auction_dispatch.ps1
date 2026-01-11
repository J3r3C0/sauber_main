# Test Auction Broker Dispatch Integration
# This script tests the complete flow: Core -> Broker -> Host

Write-Host "=== Testing Auction Broker Dispatch ===" -ForegroundColor Cyan

$baseUrl = "http://localhost:8001/api"

# 1. Create Mission
Write-Host "`n1. Creating mission..." -ForegroundColor Yellow
$mission = Invoke-RestMethod -Uri "$baseUrl/missions" -Method Post -ContentType "application/json" -Body (@{
    title = "Test Auction Dispatch"
    description = "Testing Offgrid Broker Integration"
} | ConvertTo-Json)

$missionId = $mission.id
Write-Host "   Mission ID: $missionId" -ForegroundColor Green

# 2. Create Task
Write-Host "`n2. Creating task..." -ForegroundColor Yellow
$task = Invoke-RestMethod -Uri "$baseUrl/missions/$missionId/tasks" -Method Post -ContentType "application/json" -Body (@{
    name = "test_auction"
    kind = "llm_call"
} | ConvertTo-Json)

$taskId = $task.id
Write-Host "   Task ID: $taskId" -ForegroundColor Green

# 3. Create Job
Write-Host "`n3. Creating job..." -ForegroundColor Yellow
$job = Invoke-RestMethod -Uri "$baseUrl/tasks/$taskId/jobs" -Method Post -ContentType "application/json" -Body (@{
    payload = @{
        prompt = "Hello from auction test!"
        max_tokens = 100
    }
} | ConvertTo-Json)

$jobId = $job.id
Write-Host "   Job ID: $jobId" -ForegroundColor Green

# 4. Wait a moment for dispatch to complete
Write-Host "`n4. Waiting for dispatch..." -ForegroundColor Yellow
Start-Sleep -Seconds 3

# 5. Check Job Status
Write-Host "`n5. Checking job status..." -ForegroundColor Yellow
$jobStatus = Invoke-RestMethod -Uri "$baseUrl/jobs/$jobId" -Method Get

Write-Host "`n=== Job Result ===" -ForegroundColor Cyan
Write-Host "Status: $($jobStatus.status)" -ForegroundColor $(if ($jobStatus.status -eq "completed") { "Green" } else { "Red" })
Write-Host "Result:" -ForegroundColor White
$jobStatus.result | ConvertTo-Json -Depth 5

if ($jobStatus.result.offgrid_receipt) {
    Write-Host "`n✓ SUCCESS: Job was dispatched via Offgrid!" -ForegroundColor Green
    Write-Host "  Host: $($jobStatus.result.host)" -ForegroundColor Green
    Write-Host "  Node: $($jobStatus.result.offgrid_receipt.node_id)" -ForegroundColor Green
} else {
    Write-Host "`n⚠ WARNING: Job was processed locally (not via Offgrid)" -ForegroundColor Yellow
}

