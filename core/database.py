import sqlite3
import json
from contextlib import contextmanager
from core.config import DB_PATH

def init_db():
    conn = sqlite3.connect(DB_PATH)
    # Enable WAL mode for better concurrency
    conn.execute("PRAGMA journal_mode=WAL")
    cursor = conn.cursor()
    
    # Missions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS missions (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            user_id TEXT NOT NULL,
            status TEXT DEFAULT 'planned',
            metadata TEXT DEFAULT '{}',
            tags TEXT DEFAULT '[]',
            created_at TEXT NOT NULL
        )
    """)
    
    # Tasks table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            mission_id TEXT NOT NULL,
            name TEXT NOT NULL,
            description TEXT,
            kind TEXT NOT NULL,
            params TEXT DEFAULT '{}',
            created_at TEXT NOT NULL,
            FOREIGN KEY (mission_id) REFERENCES missions (id) ON DELETE CASCADE
        )
    """)
    
    # Jobs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            payload TEXT DEFAULT '{}',
            status TEXT DEFAULT 'pending',
            result TEXT,
            retry_count INTEGER DEFAULT 0,
            priority TEXT DEFAULT 'normal',
            timeout_seconds INTEGER DEFAULT 300,
            depends_on TEXT DEFAULT '[]',
            idempotency_key TEXT UNIQUE,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (task_id) REFERENCES tasks (id) ON DELETE CASCADE
        )
    """)

    # --- MIGRATION: Add new columns if they don't exist ---
    for col, col_type in [("priority", "TEXT DEFAULT 'normal'"), 
                          ("timeout_seconds", "INTEGER DEFAULT 300"), 
                          ("depends_on", "TEXT DEFAULT '[]'")]:
        try:
            cursor.execute(f"ALTER TABLE jobs ADD COLUMN {col} {col_type}")
        except sqlite3.OperationalError:
            pass # Column already exists

    # --- MIGRATION: Missions ---
    try:
        cursor.execute("ALTER TABLE missions ADD COLUMN status TEXT DEFAULT 'planned'")
    except sqlite3.OperationalError:
        pass

    # Rate Limit Config table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS rate_limit_config (
            source TEXT PRIMARY KEY,
            max_jobs_per_minute INTEGER NOT NULL,
            max_concurrent_jobs INTEGER NOT NULL,
            current_count INTEGER DEFAULT 0,
            window_start TEXT NOT NULL
        )
    """)
    
    # Phase 10.1: Chain Context table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chain_context (
            chain_id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            state TEXT NOT NULL DEFAULT 'running',
            limits_json TEXT NOT NULL,
            artifacts_json TEXT NOT NULL,
            error_json TEXT,
            needs_tick INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)
    
    # Phase 10.1: Chain Specs table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chain_specs (
            spec_id TEXT PRIMARY KEY,
            chain_id TEXT NOT NULL,
            task_id TEXT NOT NULL,
            root_job_id TEXT NOT NULL,
            parent_job_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            params_json TEXT NOT NULL,
            resolved_params_json TEXT,
            resolved INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'pending',
            dedupe_key TEXT NOT NULL,
            dispatched_job_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            UNIQUE(chain_id, dedupe_key)
        )
    """)
    
    # Phase 10.1: Indexes for chain_specs
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_chain_specs_chain_status
        ON chain_specs(chain_id, status)
    """)
    
    # --- MIGRATION: Phase 10.2: Chain Claiming & Tracking ---
    try:
        cursor.execute("ALTER TABLE chain_context ADD COLUMN last_tick_at TEXT")
    except sqlite3.OperationalError:
        pass
    
    try:
        cursor.execute("ALTER TABLE chain_specs ADD COLUMN claim_id TEXT")
    except sqlite3.OperationalError:
        pass
        
    try:
        cursor.execute("ALTER TABLE chain_specs ADD COLUMN claimed_until TEXT")
    except sqlite3.OperationalError:
        pass

    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_chain_specs_claimed
        ON chain_specs(chain_id, status, claimed_until)
    """)

    # Track A2: Hosts table for Attestation
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS hosts (
            id TEXT PRIMARY KEY,
            status TEXT,
            health TEXT DEFAULT 'GREEN',
            last_seen TEXT,
            attestation_json TEXT DEFAULT '{}',
            metadata_json TEXT DEFAULT '{}'
        )
    """)
    
    # --- SCHEMA MIGRATIONS TABLE ---
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL,
            description TEXT
        )
    """)
    
    # Register baseline migration if not exists
    cursor.execute("""
        INSERT OR IGNORE INTO schema_migrations (version, applied_at, description)
        VALUES ('baseline_v1', datetime('now'), 'Initial schema with missions, tasks, jobs, chains')
    """)
    
    conn.commit()
    
    # Log DB info for debugging
    table_count = cursor.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0]
    print(f"[database] Initialized at {DB_PATH}")
    print(f"[database] Tables: {table_count}")
    print(f"[database] WAL mode: enabled")
    
    conn.close()

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    # PRAGMAs for performance and concurrency (per connection)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=NORMAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA temp_store=MEMORY")
    
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

if __name__ == "__main__":
    print(f"Initializing database at {DB_PATH}...")
    init_db()
    print("Database initialized successfully.")
