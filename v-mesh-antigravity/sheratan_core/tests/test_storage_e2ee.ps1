# test_storage_e2ee.ps1
# Verifies that Sheratan Core performs E2EE when replicating to Offgrid nodes.

echo "=== E2EE Storage Verification ==="

# 1. Create a Mission via Core API
echo "Creating Mission via Core (API)..."
$mission_payload = @{
    title = "E2EE Secret Mission"
    description = "This data should be encrypted on the host."
} | ConvertTo-Json

$resp = Invoke-WebRequest -Uri "http://localhost:8001/api/missions" `
    -Method Post `
    -Body $mission_payload `
    -ContentType "application/json" -ErrorAction Stop

$mission = $resp.Content | ConvertFrom-Json
$mission_id = $mission.id
echo "✓ Mission Created: $mission_id"

echo "Waiting for replication (3s)..."
Start-Sleep -Seconds 3

# 2. Check Host-A Memory directly (Query)
echo "Checking raw data on Host-A (Port 8081)..."
$query_resp = Invoke-WebRequest -Uri "http://localhost:8081/memory/query?limit=10" -Method Get
$events = ($query_resp.Content | ConvertFrom-Json).events

$search_key = "mission:$mission_id"
$target_ev = $null
foreach ($ev in $events) {
    if ($ev.meta.key -eq $search_key) {
        $target_ev = $ev
        break
    }
}

if ($null -eq $target_ev) {
    echo "✗ ERROR: Mission not found in Offgrid Memory."
    exit 1
}

# 3. Fetch raw ciphertext from Host-A
echo "✓ Found mission in Memory. Fetching raw bytes (eid: $($target_ev.eid))..."
$blob_resp = Invoke-WebRequest -Uri "http://localhost:8081/memory/payload/$($target_ev.eid)" -Method Get
$raw_content = $blob_resp.Content

# 4. Verify it is JSON and has 'ciphertext' (not raw mission JSON)
try {
    $blob_obj = $raw_content | ConvertFrom-Json
    if ($blob_obj.ciphertext) {
        echo "✓ SUCCESS: Data is ENCRYPTED (E2EE active)."
        echo "  Nonce: $($blob_obj.nonce)"
        echo "  AAD: $($blob_obj.aad)"
    } else {
        echo "✗ ERROR: Data is NOT encrypted! Found raw JSON."
        exit 1
    }
} catch {
    echo "✗ ERROR: Host returned invalid data format."
    exit 1
}

echo "=== Verification COMPLETE: Proper E2EE Integration confirmed. ==="
