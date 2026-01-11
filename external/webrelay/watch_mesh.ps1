$root = "C:/projectroot"
$inbox = "$root/runtime/input/trigger.json"
$archive = "$root/runtime/archive/"
$ledgerFile = "$root/runtime/output/ledger.jsonl"

if (!(Test-Path $archive)) { New-Item -ItemType Directory -Path $archive }

function Write-RealityLog($evtName, $jobId, $zone, $artifactPath, $meta) {
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

Write-Host "V-Mesh Auditor-Mode aktiv. Warte auf trigger.json..." -ForegroundColor Cyan

while ($true) {
    if (Test-Path $inbox) {
        Write-Host "[!] Neuer Job erkannt. Lade Inhalt..." -ForegroundColor Yellow
        $content = Get-Content $inbox -Raw
        $json = $content | ConvertFrom-Json
        $jobId = $json.v_metadata.job_id
        
        Write-RealityLog -evtName "EXEC_CLAIMED" -jobId $jobId -zone "input" -artifactPath $inbox
        
        # Hier wird der Inhalt für mich ausgegeben
        Write-Host "--- INHALT START ---"
        $content
        Write-Host "--- INHALT ENDE ---"
        
        # Verschiebe in den Archiv-Ordner, um den Loop zu stoppen (WICHTIG!)
        $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
        Move-Item -Path $inbox -Destination "$archive/job_$timestamp.json"
        
        Write-RealityLog -evtName "EXEC_COMPLETED" -jobId $jobId -zone "archive" -artifactPath "$archive/job_$timestamp.json"
        
        Write-Host "[OK] Job archiviert. System im Leerlauf, bis die Lösung eintrifft." -ForegroundColor Green
        break # Stoppt den Loop nach einem Job, um 1:3:9 zu verhindern
    }
    Start-Sleep -Seconds 2
}
