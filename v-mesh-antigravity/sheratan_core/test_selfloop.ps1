# Sheratan Self-Loop Test Script (PowerShell)
# ==================================================

Write-Host "🔄 Sheratan Self-Loop Test Script" -ForegroundColor Cyan
Write-Host "====================================`n"

# 1. Mission erstellen
Write-Host "1️⃣  Creating Mission..." -ForegroundColor Yellow
$missionBody = @{
    title = "Test Self-Loop"
    description = "First Self-Loop test run - $(Get-Date)"
    metadata = @{}
    tags = @()
} | ConvertTo-Json

try {
    $mission = Invoke-RestMethod -Uri "http://localhost:8001/api/missions" `
        -Method Post `
        -ContentType "application/json" `
        -Body $missionBody
    
    $missionId = $mission.id
    Write-Host "   ✅ Mission created: $missionId`n" -ForegroundColor Green
}
catch {
    Write-Host "   ❌ Failed to create mission: $_" -ForegroundColor Red
    exit 1
}

# 2. Task erstellen
Write-Host "2️⃣  Creating Task..." -ForegroundColor Yellow
$taskBody = @{
    name = "selfloop_task"
    kind = "selfloop"
    description = "Self-Loop Task"
    params = @{}
} | ConvertTo-Json

try {
    $task = Invoke-RestMethod -Uri "http://localhost:8001/api/missions/$missionId/tasks" `
        -Method Post `
        -ContentType "application/json" `
        -Body $taskBody
    
    $taskId = $task.id
    Write-Host "   ✅ Task created: $taskId`n" -ForegroundColor Green
}
catch {
    Write-Host "   ❌ Failed to create task: $_" -ForegroundColor Red
    exit 1
}

# 3. Self-Loop Job erstellen
Write-Host "3️⃣  Creating Self-Loop Job..." -ForegroundColor Yellow
$jobBody = @{
    payload = @{
        job_type = "sheratan_selfloop"
        goal = "Analyze the Sheratan system and suggest 3 concrete improvements"
        core_data = "Sheratan is a multi-agent system with LCP protocol. Current focus: Self-Loop integration testing."
        current_task = "First iteration: Understand current system state and identify improvement opportunities"
        loop_state = @{
            iteration = 1
            history_summary = ""
            open_questions = @()
            constraints = @(
                "Keep suggestions practical and implementable"
                "Focus on actual Sheratan architecture"
            )
        }
        max_iterations = 3
    }
} | ConvertTo-Json -Depth 10

try {
    $job = Invoke-RestMethod -Uri "http://localhost:8001/api/tasks/$taskId/jobs" `
        -Method Post `
        -ContentType "application/json" `
        -Body $jobBody
    
    $jobId = $job.id
    Write-Host "   ✅ Job created: $jobId`n" -ForegroundColor Green
}
catch {
    Write-Host "   ❌ Failed to create job: $_" -ForegroundColor Red
    exit 1
}

# 4. Job dispatchen
Write-Host "4️⃣  Dispatching Job to LLM..." -ForegroundColor Yellow
try {
    Invoke-RestMethod -Uri "http://localhost:8001/api/jobs/$jobId/dispatch" -Method Post | Out-Null
    Write-Host "   ✅ Job dispatched! Self-Loop starting...`n" -ForegroundColor Green
}
catch {
    Write-Host "   ❌ Failed to dispatch job: $_" -ForegroundColor Red
    exit 1
}

# 5. Warten und Results anzeigen
Write-Host "5️⃣  Waiting for LLM response..." -ForegroundColor Yellow
Write-Host "   (Self-Loop will auto-create follow-up jobs)`n"

for ($i = 1; $i -le 30; $i++) {
    Start-Sleep -Seconds 2
    
    try {
        $allJobs = Invoke-RestMethod -Uri "http://localhost:8001/api/jobs"
        $selfloopJobs = $allJobs | Where-Object { 
            $_.task_id -eq $taskId -and 
            $_.payload.job_type -eq "sheratan_selfloop" 
        }
        
        $doneCount = ($selfloopJobs | Where-Object { $_.status -eq "done" }).Count
        $totalCount = $selfloopJobs.Count
        
        Write-Host "`r   Progress: $doneCount/$totalCount jobs done (checking... $i/30)" -NoNewline
        
        # Wenn alle 3 Iterationen done sind, stoppen
        if ($doneCount -eq 3) {
            Write-Host "`n   ✅ All 3 iterations completed!`n" -ForegroundColor Green
            break
        }
    }
    catch {
        Write-Host "`r   ⏳ Checking... $i/30" -NoNewline
    }
}

# 6. Final Results
Write-Host "`n6️⃣  Final Results:" -ForegroundColor Yellow
Write-Host "   ============================================`n"

try {
    $allJobs = Invoke-RestMethod -Uri "http://localhost:8001/api/jobs"
    $selfloopJobs = $allJobs | Where-Object { 
        $_.task_id -eq $taskId -and 
        $_.payload.job_type -eq "sheratan_selfloop" 
    }
    
    foreach ($j in $selfloopJobs | Sort-Object created_at) {
        $iteration = $j.payload.loop_state.iteration
        $status = $j.status
        
        $statusColor = switch ($status) {
            "done" { "Green" }
            "failed" { "Red" }
            "pending" { "Yellow" }
            default { "White" }
        }
        
        Write-Host "   Job $($j.id.Substring(0,8))..." -NoNewline
        Write-Host " Iteration $iteration" -NoNewline
        Write-Host " [$status]" -ForegroundColor $statusColor
        
        if ($status -eq "done" -and $j.result) {
            # Versuche A/B/C/D zu extrahieren (vereinfacht)
            $resultText = $j.result | ConvertTo-Json -Depth 10
            if ($resultText -match 'A\)') {
                Write-Host "      └─ Has A/B/C/D sections ✓" -ForegroundColor DarkGray
            }
        }
    }
    
    Write-Host "`n   📊 Summary:" -ForegroundColor Cyan
    Write-Host "      Total Jobs: $($selfloopJobs.Count)"
    Write-Host "      Done: $(($selfloopJobs | Where-Object {$_.status -eq 'done'}).Count)"
    Write-Host "      Failed: $(($selfloopJobs | Where-Object {$_.status -eq 'failed'}).Count)"
    Write-Host "      Pending: $(($selfloopJobs | Where-Object {$_.status -eq 'pending'}).Count)"
}
catch {
    Write-Host "   ❌ Failed to get results: $_" -ForegroundColor Red
}

Write-Host "`n✅ Test complete!" -ForegroundColor Green
Write-Host "   View details: http://localhost:5174 (React Dashboard)`n"
