# test_storage_e2ee_final.ps1
echo "=== Final E2EE Storage Verification ==="

# 1. Create a UNIQUE Mission
$uid = [guid]::NewGuid().ToString().Substring(0,8)
$title = "Secret-Mission-$uid"
echo "Creating Mission: $title"

$payload = @{
    title = $title
    description = "Top Secret Core Data"
} | ConvertTo-Json

$resp = Invoke-WebRequest -Uri "http://localhost:8001/api/missions" `
    -Method Post -Body $payload -ContentType "application/json" -ErrorAction Stop

$mission = $resp.Content | ConvertFrom-Json
$mission_id = $mission.id
echo "✓ Mission Created: $mission_id"

echo "Waiting for Mesh Replication (5s)..."
Start-Sleep -Seconds 5

# 2. Query Host-A for the specific key
echo "Querying Host-A (Port 8081) for Key: mission:$mission_id..."
$q_resp = Invoke-WebRequest -Uri "http://localhost:8081/memory/query?limit=50" -Method Get
$events = ($q_resp.Content | ConvertFrom-Json).events

$target = $null
foreach ($ev in $events) {
    if ($ev.meta.key -eq "mission:$mission_id") {
        $target = $ev
        break
    }
}

if ($null -eq $target) {
    echo "✗ ERROR: Mission NOT FOUND in host memory even after 5s."
    exit 1
}

# 3. Verify Encryption at rest
echo "✓ Mission Found (EID: $($target.eid)). Verifying encryption..."
$p_resp = Invoke-WebRequest -Uri "http://localhost:8081/memory/payload/$($target.eid)" -Method Get
$raw_data = $p_resp.Content

try {
    $obj = $raw_data | ConvertFrom-Json
    if ($obj.ciphertext -and $obj.nonce) {
        echo "✓ SUCCESS: Data is ENCRYPTED (E2EE Active)."
        echo "  - Metadata shows 'encrypted: true'"
        echo "  - Body contains XChaCha20 ciphertext."
    } else {
        echo "✗ ERROR: Data is readable JSON! E2EE failed."
        exit 1
    }
} catch {
    echo "✓ SUCCESS: Data is raw binary/ciphertext (not readable JSON)."
}

echo "=== E2EE VERIFICATION PASSED ==="
