import os
import sqlite3

def create_test_db(db_path: str):
    if os.path.exists(db_path):
        os.remove(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS memories (
        id TEXT PRIMARY KEY,
        namespace TEXT NOT NULL,
        subject TEXT NOT NULL,
        predicate TEXT NOT NULL,
        value TEXT NOT NULL,
        memory_type TEXT NOT NULL,
        source_text TEXT,
        importance REAL DEFAULT 0.5,
        created_at DATETIME,
        updated_at DATETIME,
        last_accessed_at DATETIME,
        status TEXT DEFAULT 'active',
        supersedes_id TEXT,
        metadata TEXT
    );
    """)
    conn.commit()
    conn.close()
