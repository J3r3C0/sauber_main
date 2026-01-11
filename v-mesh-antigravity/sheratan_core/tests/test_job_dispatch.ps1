# PowerShell Test Script für Job Dispatch Integration
# Testet: Core → Offgrid Broker → Host

Write-Host "=== Sheratan Job Dispatch Integration Test ===" -ForegroundColor Cyan
Write-Host ""

# Set Offgrid environment
$env:OFFGRID_MODE = "auto"
$env:OFFGRID_BROKER_URL = "http://127.0.0.1:9000"
$env:OFFGRID_AUTH_KEY = "shared-secret"

# Test 1: Check if Broker is running
Write-Host "Test 1: Checking Broker status..." -ForegroundColor Yellow
try {
    $brokerStatus = Invoke-WebRequest -Uri "http://127.0.0.1:9000/status" -Method GET
    $statusData = $brokerStatus.Content | ConvertFrom-Json
    Write-Host "  ✓ Broker is running: $($statusData.service) v$($statusData.version)" -ForegroundColor Green
}
catch {
    Write-Host "  ✗ Broker is not running" -ForegroundColor Red
    exit 1
}

# Test 2: Check Hosts
Write-Host ""
Write-Host "Test 2: Checking Offgrid Hosts..." -ForegroundColor Yellow
foreach ($port in @(8081, 8082)) {
    try {
        $hostStatus = Invoke-WebRequest -Uri "http://127.0.0.1:$port/announce" -Method GET
        $hostData = $hostStatus.Content | ConvertFrom-Json
        Write-Host "  ✓ Host on port $port is active: $($hostData.node_id)" -ForegroundColor Green
    }
    catch {
        Write-Host "  ✗ Host on port $port is not responding" -ForegroundColor Red
    }
}

# Test 3: Create Mission
Write-Host ""
Write-Host "Test 3: Creating Mission via Core..." -ForegroundColor Yellow
$missionBody = @{
    title       = "PowerShell Test - Offgrid Integration"
    description = "Testing Job Dispatch to Offgrid"
} | ConvertTo-Json

try {
    $mission = Invoke-WebRequest -Uri "http://localhost:8001/api/missions" `
        -Method POST `
        -Headers @{"Content-Type" = "application/json" } `
        -Body $missionBody
    
    $missionData = $mission.Content | ConvertFrom-Json
    Write-Host "  ✓ Mission created: $($missionData.id)" -ForegroundColor Green
    $missionId = $missionData.id
}
catch {
    Write-Host "  ✗ Failed to create mission: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test 4: Create Task
Write-Host ""
Write-Host "Test 4: Creating Task..." -ForegroundColor Yellow
$taskBody = @{
    name        = "llm_call"
    description = "Test task for Offgrid dispatch"
    kind        = "llm_call"
    params      = @{}
} | ConvertTo-Json

try {
    $task = Invoke-WebRequest -Uri "http://localhost:8001/api/missions/$missionId/tasks" `
        -Method POST `
        -Headers @{"Content-Type" = "application/json" } `
        -Body $taskBody
    
    $taskData = $task.Content | ConvertFrom-Json
    Write-Host "  ✓ Task created: $($taskData.id)" -ForegroundColor Green
    $taskId = $taskData.id
}
catch {
    Write-Host "  ✗ Failed to create task: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test 5: Create Job
Write-Host ""
Write-Host "Test 5: Creating Job..." -ForegroundColor Yellow
$jobBody = @{
    payload = @{
        prompt = "Hello from PowerShell! Testing Offgrid Integration."
    }
} | ConvertTo-Json

try {
    $job = Invoke-WebRequest -Uri "http://localhost:8001/api/tasks/$taskId/jobs" `
        -Method POST `
        -Headers @{"Content-Type" = "application/json" } `
        -Body $jobBody
    
    $jobData = $job.Content | ConvertFrom-Json
    Write-Host "  ✓ Job created: $($jobData.id)" -ForegroundColor Green
    $jobId = $jobData.id
}
catch {
    Write-Host "  ✗ Failed to create job: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test 6: Dispatch Job
Write-Host ""
Write-Host "Test 6: Dispatching Job via Offgrid..." -ForegroundColor Yellow
try {
    $dispatch = Invoke-WebRequest -Uri "http://localhost:8001/api/jobs/$jobId/dispatch" `
        -Method POST `
        -Headers @{"Content-Type" = "application/json" }
    
    Write-Host "  ✓ Job dispatched" -ForegroundColor Green
    
    # Wait a bit for processing
    Start-Sleep -Seconds 2
}
catch {
    Write-Host "  ✗ Failed to dispatch job: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

# Test 7: Check Job Result
Write-Host ""
Write-Host "Test 7: Checking Job Result..." -ForegroundColor Yellow
try {
    $result = Invoke-WebRequest -Uri "http://localhost:8001/api/jobs/$jobId" -Method GET
    $resultData = $result.Content | ConvertFrom-Json
    
    Write-Host "  Status: $($resultData.status)" -ForegroundColor Cyan
    
    if ($resultData.result) {
        Write-Host "  Result:" -ForegroundColor Cyan
        Write-Host "    - OK: $($resultData.result.ok)" -ForegroundColor White
        Write-Host "    - Host: $($resultData.result.host)" -ForegroundColor White
        
        if ($resultData.result.offgrid_receipt) {
            Write-Host "    - Receipt: " -ForegroundColor White
            Write-Host "        Node: $($resultData.result.offgrid_receipt.node_id)" -ForegroundColor White
            Write-Host "        Metrics: $($resultData.result.offgrid_receipt.metrics | ConvertTo-Json -Compress)" -ForegroundColor White
        }
    }
    
    if ($resultData.status -eq "completed") {
        Write-Host ""
        Write-Host "✓✓✓ SUCCESS! Job completed via Offgrid!" -ForegroundColor Green
    }
    else {
        Write-Host ""
        Write-Host "⚠ Job not completed yet. Status: $($resultData.status)" -ForegroundColor Yellow
    }
}
catch {
    Write-Host "  ✗ Failed to get job result: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== Test Complete ===" -ForegroundColor Cyan
