import sqlite3
import json
from contextlib import contextmanager
from core.config import DB_PATH

def init_db():
    conn = sqlite3.connect(DB_PATH)
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
    
    conn.commit()
    conn.close()

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

if __name__ == "__main__":
    print(f"Initializing database at {DB_PATH}...")
    init_db()
    print("Database initialized successfully.")
