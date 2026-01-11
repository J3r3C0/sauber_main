# Simple Offgrid Test
Write-Host "=== Simple Offgrid Test ===" -ForegroundColor Cyan

# Check Core is running
try {
    $status = Invoke-WebRequest -Uri "http://localhost:8001/api/status" -Method GET
    Write-Host "✓ Core is running" -ForegroundColor Green
}
catch {
    Write-Host "✗ Core is not running" -ForegroundColor Red
    exit 1
}

# Create Mission
Write-Host "`nCreating Mission..." -ForegroundColor Yellow
$missionBody = '{"title":"Test","description":"Test"}'
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/missions" `
        -Method POST `
        -ContentType "application/json" `
        -Body $missionBody
    
    Write-Host "✓ Mission: $($response.id)" -ForegroundColor Green
    $missionId = $response.id
}
catch {
    Write-Host "✗ Failed: $_" -ForegroundColor Red
    exit 1
}

# Create Task
Write-Host "Creating Task..." -ForegroundColor Yellow
$taskBody = '{"name":"test","description":"Test","kind":"llm_call","params":{}}'
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/missions/$missionId/tasks" `
        -Method POST `
        -ContentType "application/json" `
        -Body $taskBody
    
    Write-Host "✓ Task: $($response.id)" -ForegroundColor Green
    $taskId = $response.id
}
catch {
    Write-Host "✗ Failed: $_" -ForegroundColor Red
    exit 1
}

# Create Job
Write-Host "Creating Job..." -ForegroundColor Yellow
$jobBody = '{"payload":{"prompt":"Test"}}'
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/tasks/$taskId/jobs" `
        -Method POST `
        -ContentType "application/json" `
        -Body $jobBody
    
    Write-Host "✓ Job: $($response.id)" -ForegroundColor Green
    $jobId = $response.id
}
catch {
    Write-Host "✗ Failed: $_" -ForegroundColor Red
    exit 1
}

# Dispatch Job
Write-Host "Dispatching Job..." -ForegroundColor Yellow
try {
    $response = Invoke-RestMethod -Uri "http://localhost:8001/api/jobs/$jobId/dispatch" `
        -Method POST `
        -ContentType "application/json"
    
    Write-Host "✓ Dispatched via: $($response.method)" -ForegroundColor Green
    
    if ($response.method -eq "offgrid") {
        Write-Host "  Status: $($response.status)" -ForegroundColor Cyan
    }
    else {
        Write-Host "  File: $($response.job_file)" -ForegroundColor Cyan
    }
}
catch {
    Write-Host "✗ Failed: $_" -ForegroundColor Red
    exit 1
}

# Check Result
Start-Sleep -Seconds 2
Write-Host "`nChecking Result..." -ForegroundColor Yellow
try {
    $job = Invoke-RestMethod -Uri "http://localhost:8001/api/jobs/$jobId" -Method GET
    
    Write-Host "Status: $($job.status)" -ForegroundColor Cyan
    
    if ($job.result) {
        Write-Host "Result:" -ForegroundColor Cyan
        Write-Host "  OK: $($job.result.ok)" -ForegroundColor White
        Write-Host "  Host: $($job.result.host)" -ForegroundColor White
        
        if ($job.status -eq "completed") {
            Write-Host "`n✓✓✓ SUCCESS!" -ForegroundColor Green
        }
    }
}
catch {
    Write-Host "✗ Failed: $_" -ForegroundColor Red
}

Write-Host "`n=== Done ===" -ForegroundColor Cyan
