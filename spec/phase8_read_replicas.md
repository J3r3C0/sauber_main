# Phase 8 Read-Replicas Specification

## Overview
Single-writer, multi-reader architecture using byte-offset-based journal sync.

## Writer HTTP API

### Endpoints

#### `GET /health`
Returns writer status and journal metadata.

**Response:**
```json
{
  "status": "ok",
  "journal_size_bytes": 1234567,
  "last_hash": "abc123...",
  "last_event_ts": 1704931200.0,
  "total_events": 5432
}
```

#### `GET /journal?offset=<int>`
Serves journal content starting from byte offset.

**Query Parameters:**
- `offset` (required): Byte offset to start reading from

**Response Headers:**
- `X-Journal-Next-Offset`: Next byte offset to request
- `X-Journal-Last-Hash`: Hash of last complete event in response
- `X-Journal-Last-TS`: Timestamp of last complete event

**Response Body:**
- `Content-Type: text/plain; charset=utf-8`
- Raw JSONL content (complete lines only)

**Partial Line Handling:**
- Writer MUST only send complete lines (ending with `\n`)
- If file ends mid-line, truncate response at last complete line
- Client will re-request same offset on next sync

## Replica State File

**Path:** `replica_state.json`

**Format:**
```json
{
  "writer_url": "http://writer-node:8100",
  "sync_offset": 1234567,
  "last_hash": "abc123...",
  "last_event_ts": 1704931200.0,
  "last_sync_at": 1704931250.0,
  "total_events_synced": 5432
}
```

## Sync Algorithm

### Replica Startup
1. Load `replica_state.json` (or init with offset=0)
2. Load existing `ledger.json` state
3. Start sync loop

### Sync Loop (every N seconds)
1. **Fetch chunk:**
   ```python
   resp = GET {writer_url}/journal?offset={sync_offset}
   chunk = resp.text
   next_offset = int(resp.headers['X-Journal-Next-Offset'])
   ```

2. **Handle partial lines:**
   ```python
   # If we have buffered partial line from previous sync
   if partial_buffer:
       chunk = partial_buffer + chunk
       partial_buffer = ""
   
   # Check if chunk ends mid-line
   if chunk and not chunk.endswith('\n'):
       # Find last complete line
       last_newline = chunk.rfind('\n')
       if last_newline >= 0:
           partial_buffer = chunk[last_newline+1:]
           chunk = chunk[:last_newline+1]
       else:
           # Entire chunk is partial, buffer it
           partial_buffer = chunk
           chunk = ""
   ```

3. **Parse and apply events:**
   ```python
   for line in chunk.splitlines():
       if not line.strip(): continue
       event = json.loads(line)
       apply_event_to_state(state, event)
   ```

4. **Update replica state:**
   ```python
   replica_state['sync_offset'] = next_offset
   replica_state['last_hash'] = resp.headers['X-Journal-Last-Hash']
   replica_state['last_event_ts'] = float(resp.headers['X-Journal-Last-TS'])
   replica_state['last_sync_at'] = time.time()
   save_replica_state()
   ```

5. **Optional: Verify chain integrity**
   ```python
   # Only verify new events, not entire journal
   verify_chain_segment(new_events)
   ```

## Governance Polish (Schritt 0)

### Environment Variables

```bash
# Governance Master Switch
GOV_ENABLED=1                    # 0=disable all governance, 1=enable

# Dry-Run Mode
GOV_DRY_RUN=0                    # 1=log margins only, don't apply

# Rate Limiting
SETTLEMENT_RATE_LIMIT_PER_MIN=100  # Max settlements per minute

# Replica Safety
REPLICA_READONLY_ENFORCED=1      # Replicas MUST NOT write, even if misconfigured
```

### LedgerConfig Updates

```python
@dataclass
class LedgerConfig:
    # ... existing fields ...
    
    # Governance
    gov_enabled: bool = True
    gov_dry_run: bool = False
    settlement_rate_limit: int = 100  # per minute
    
    # Multi-Node
    mode: str = "writer"  # "writer" or "replica"
    writer_url: Optional[str] = None
    sync_interval: int = 5  # seconds
    readonly_enforced: bool = True
```

## Error Handling

### Writer Unreachable
- Replica continues serving stale data
- Health endpoint reports: `{"writer_reachable": false, "sync_lag_s": 123}`

### Corrupted Journal
- Replica detects hash mismatch
- Logs error, stops sync
- Requires manual intervention (re-sync from snapshot)

### Partial Line Buffer Overflow
- If partial_buffer > 1MB, log warning (likely corruption)
- Clear buffer and re-sync from last known good offset

## Deployment

### Writer Node
```bash
LEDGER_MODE=writer
LEDGER_JOURNAL_HTTP_PORT=8100
GOV_ENABLED=1
GOV_DRY_RUN=0
```

### Replica Node
```bash
LEDGER_MODE=replica
LEDGER_WRITER_URL=http://writer-node:8100
LEDGER_SYNC_INTERVAL=5
REPLICA_READONLY_ENFORCED=1
```
