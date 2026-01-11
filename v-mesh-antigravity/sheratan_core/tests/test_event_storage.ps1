# test_event_storage.ps1
# Verifies Event-Type integration and Outbox persistence

echo "=== Event-Based Storage Verification ==="

# 1. Create a Mission
echo "Creating Mission..."
$mission_payload = @{
    title = "Event Test Mission"
    description = "Testing semantic event types"
} | ConvertTo-Json

$resp = Invoke-WebRequest -Uri "http://localhost:8001/api/missions" `
    -Method Post `
    -Body $mission_payload `
    -ContentType "application/json" -ErrorAction Stop

$mission = $resp.Content | ConvertFrom-Json
$mission_id = $mission.id
echo "✓ Mission Created: $mission_id"

echo "Waiting for outbox processing (5s)..."
Start-Sleep -Seconds 5

# 2. Check Outbox DB
echo "Checking Outbox DB..."
if (Test-Path ".\core\data\outbox.db") {
    echo "✓ Outbox DB exists"
} else {
    echo "✗ ERROR: Outbox DB not found"
    exit 1
}

# 3. Query Host-A for the event
echo "Querying Host-A for event..."
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
    echo "✗ ERROR: Event not found in Host memory"
    exit 1
}

# 4. Verify Event Type
echo "✓ Event found (EID: $($target_ev.eid))"
echo "  Event Type: $($target_ev.etype)"
echo "  Metadata: $($target_ev.meta | ConvertTo-Json -Compress)"

if ($target_ev.etype -eq 10) {
    echo "✓ SUCCESS: Correct etype (10 = MISSION_CREATED)"
} else {
    echo "✗ ERROR: Wrong etype. Expected 10, got $($target_ev.etype)"
    exit 1
}

# 5. Verify E2EE
if ($target_ev.meta.encrypted -eq $true) {
    echo "✓ E2EE metadata present"
} else {
    echo "⚠ WARNING: E2EE metadata missing"
}

echo "=== Verification COMPLETE ==="
