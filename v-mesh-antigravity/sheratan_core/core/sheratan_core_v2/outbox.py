"""
Persistent outbox for Offgrid replication jobs.
Ensures replication survives Core crashes/restarts.
"""
import sqlite3
import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any


class ReplicationOutbox:
    """SQLite-based persistent queue for Offgrid replication jobs."""
    
    def __init__(self, db_path: str = "./data/outbox.db"):
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(db_path, check_same_thread=False, timeout=30)
        self._init_db()
    
    def _init_db(self):
        """Initialize outbox schema."""
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS outbox (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT NOT NULL,
                data_json TEXT NOT NULL,
                etype INTEGER NOT NULL,
                required_acks REAL NOT NULL,
                created_ts INTEGER NOT NULL,
                retry_count INTEGER DEFAULT 0,
                last_error TEXT,
                status TEXT DEFAULT 'pending'
            )
        """)
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_status ON outbox(status)")
        self.conn.commit()
    
    def enqueue(self, key: str, data: dict, etype: int, required_acks: float = 1.0):
        """Add a replication job to the outbox."""
        ts = int(time.time() * 1000)
        self.conn.execute(
            "INSERT INTO outbox (key, data_json, etype, required_acks, created_ts) VALUES (?, ?, ?, ?, ?)",
            (key, json.dumps(data), etype, required_acks, ts)
        )
        self.conn.commit()
        print(f"[outbox] Enqueued {key} (etype={etype})")
    
    def get_pending(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch pending jobs for processing."""
        cur = self.conn.execute(
            "SELECT id, key, data_json, etype, required_acks, retry_count FROM outbox WHERE status='pending' ORDER BY created_ts ASC LIMIT ?",
            (limit,)
        )
        return [
            {
                "id": r[0],
                "key": r[1],
                "data": json.loads(r[2]),
                "etype": r[3],
                "required_acks": r[4],
                "retry_count": r[5]
            }
            for r in cur.fetchall()
        ]
    
    def mark_success(self, job_id: int):
        """Mark a job as successfully replicated."""
        self.conn.execute("UPDATE outbox SET status='completed' WHERE id=?", (job_id,))
        self.conn.commit()
    
    def mark_failed(self, job_id: int, error: str):
        """Increment retry count and log error."""
        self.conn.execute(
            "UPDATE outbox SET retry_count=retry_count+1, last_error=? WHERE id=?",
            (error, job_id)
        )
        self.conn.commit()
    
    def cleanup_old(self, max_age_hours: int = 24):
        """Remove completed jobs older than max_age_hours."""
        cutoff = int(time.time() * 1000) - (max_age_hours * 3600 * 1000)
        deleted = self.conn.execute(
            "DELETE FROM outbox WHERE status='completed' AND created_ts < ?",
            (cutoff,)
        ).rowcount
        self.conn.commit()
        if deleted > 0:
            print(f"[outbox] Cleaned up {deleted} old jobs")
