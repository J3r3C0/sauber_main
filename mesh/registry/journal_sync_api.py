"""
Writer HTTP API for Journal Sync.

Serves journal segments via HTTP for replica nodes to consume.
"""
import os
from pathlib import Path
from fastapi import FastAPI, Query, Response
from fastapi.responses import PlainTextResponse
import uvicorn

app = FastAPI(title="Ledger Journal Sync API")

# Configuration
JOURNAL_PATH = Path(os.getenv("LEDGER_JOURNAL_PATH", "ledger_events.jsonl"))

@app.get("/health")
def health():
    """Returns writer status and journal metadata."""
    if not JOURNAL_PATH.exists():
        return {
            "status": "ok",
            "journal_size_bytes": 0,
            "last_hash": None,
            "last_event_ts": None,
            "total_events": 0
        }
    
    size = JOURNAL_PATH.stat().st_size
    
    # Read last line to get metadata
    last_hash = None
    last_ts = None
    total_events = 0
    
    try:
        with open(JOURNAL_PATH, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    total_events += 1
            # Go back to read last line
            f.seek(max(0, size - 1024))
            lines = f.readlines()
            if lines:
                import json
                last_event = json.loads(lines[-1])
                last_hash = last_event.get("hash")
                last_ts = last_event.get("ts")
    except Exception:
        pass
    
    return {
        "status": "ok",
        "journal_size_bytes": size,
        "last_hash": last_hash,
        "last_event_ts": last_ts,
        "total_events": total_events
    }

@app.get("/journal")
def get_journal(offset: int = Query(0, ge=0)):
    """
    Serves journal content starting from byte offset.
    Only returns complete lines (ending with newline).
    """
    if not JOURNAL_PATH.exists():
        return PlainTextResponse(
            content="",
            headers={
                "X-Journal-Next-Offset": "0",
                "X-Journal-Last-Hash": "",
                "X-Journal-Last-TS": "0"
            }
        )
    
    file_size = JOURNAL_PATH.stat().st_size
    
    if offset >= file_size:
        # Already at end
        return PlainTextResponse(
            content="",
            headers={
                "X-Journal-Next-Offset": str(file_size),
                "X-Journal-Last-Hash": "",
                "X-Journal-Last-TS": "0"
            }
        )
    
    # Read from offset to end
    with open(JOURNAL_PATH, 'rb') as f:
        f.seek(offset)
        chunk = f.read()
    
    # Decode and find last complete line
    try:
        text = chunk.decode('utf-8')
    except UnicodeDecodeError:
        # Partial UTF-8 sequence, truncate
        text = chunk.decode('utf-8', errors='ignore')
    
    # Only return complete lines
    if text and not text.endswith('\n'):
        last_newline = text.rfind('\n')
        if last_newline >= 0:
            text = text[:last_newline + 1]
        else:
            # No complete lines in this chunk
            text = ""
    
    next_offset = offset + len(text.encode('utf-8'))
    
    # Extract last hash and ts
    last_hash = ""
    last_ts = "0"
    if text.strip():
        lines = text.strip().split('\n')
        if lines:
            import json
            try:
                last_event = json.loads(lines[-1])
                last_hash = last_event.get("hash", "")
                last_ts = str(last_event.get("ts", 0))
            except Exception:
                pass
    
    return PlainTextResponse(
        content=text,
        headers={
            "X-Journal-Next-Offset": str(next_offset),
            "X-Journal-Last-Hash": last_hash,
            "X-Journal-Last-TS": last_ts
        }
    )

if __name__ == "__main__":
    port = int(os.getenv("LEDGER_JOURNAL_HTTP_PORT", "8100"))
    print(f"Starting Journal Sync API on port {port}")
    print(f"Journal path: {JOURNAL_PATH}")
    uvicorn.run(app, host="0.0.0.0", port=port)
