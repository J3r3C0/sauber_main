# v_execute.ps1 - Das Verdammungs-Modul
$root = "C:/projectroot"
$inputDir = "$root/runtime/input"
$archiveDir = "$root/runtime/archive"
$ledgerFile = "$root/runtime/output/ledger.jsonl"

if (!(Test-Path $inputDir)) { New-Item -ItemType Directory -Path $inputDir }
if (!(Test-Path $archiveDir)) { New-Item -ItemType Directory -Path $archiveDir }

function Log-Ledger($evtName, $jobId, $zone, $artifactPath, $meta) {
    $ts = [DateTime]::UtcNow.ToString("yyyy-MM-ddTHH:mm:ss.fffZ")
    $artifact = $null
    if ($artifactPath -and (Test-Path $artifactPath)) {
        $bytes = (Get-Item $artifactPath).Length
        $hash = (Get-FileHash -Path $artifactPath -Algorithm SHA256).Hash.ToLower()
        $relPath = ($artifactPath -replace [regex]::Escape($root), "").TrimStart("/").TrimStart("\").Replace("\", "/")
        $artifact = @{
            path   = $relPath
            sha256 = $hash
            bytes  = $bytes
        }
    }
    $entry = @{
        ts       = $ts
        actor    = "worker"
        event    = $evtName
        job_id   = $jobId
        trace_id = if ($jobId) { $jobId } else { "root" }
        zone     = $zone
        artifact = $artifact
        meta     = if ($meta) { $meta } else { @{} }
    }
    $line = (ConvertTo-Json $entry -Compress) + "`n"
    [System.IO.File]::AppendAllText($ledgerFile, $line)
}

Write-Host "Verdammungs-Modul aktiv. Warte auf Befehle in $inputDir..." -ForegroundColor Magenta

while ($true) {
    $files = Get-ChildItem -Path $inputDir -Filter *.json
    foreach ($file in $files) {
        try {
            $json = Get-Content $file.FullName | ConvertFrom-Json
            $jobId = $json.v_metadata.job_id
            Write-Host "[!] Führe Job aus: $jobId" -ForegroundColor Cyan
            
            Log-Ledger -event "EXEC_CLAIMED" -jobId $jobId -zone "input" -artifactPath $file.FullName
            
            # Ausführungsebene
            if ($json.execution_layer.action -eq "FILE_SYSTEM_OPERATION") {
                $params = $json.execution_layer.params
                if ($params.mode -eq "write") {
                    $targetPath = $params.target_path -replace "C:/projektroot", $root
                    $targetDir = [System.IO.Path]::GetDirectoryName($targetPath)
                    if (!(Test-Path $targetDir)) { New-Item -ItemType Directory -Path $targetDir -Force }
                    $params.payload_content | Out-File -FilePath $targetPath -Force
                    Write-Host "[OK] Datei geschrieben: $($targetPath)" -ForegroundColor Green
                    Log-Ledger -event "EXEC_COMPLETED" -jobId $jobId -zone "output" -artifactPath $targetPath -meta @{ action = "write" }
                }
            }

            # Archivierung zur Vermeidung von Doppel-Ausführung
            $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
            Move-Item -Path $file.FullName -Destination "$archiveDir/executed_$timestamp.json"
        }
        catch {
            Write-Host "[ERR] Fehler bei Job-Verarbeitung: $_" -ForegroundColor Red
        }
    }
    Start-Sleep -Seconds 1
}
