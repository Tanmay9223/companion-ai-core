import time
import sqlite3
import uuid
import os
from app.init_db import init_db
from app.memory_store import MemoryStore

def setup_db():
    db_path = "test_perf.sqlite"
    if os.path.exists(db_path):
        os.remove(db_path)
    # create table
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE memories (
            id TEXT PRIMARY KEY,
            namespace TEXT,
            subject TEXT,
            predicate TEXT,
            value TEXT,
            memory_type TEXT,
            source_text TEXT,
            importance REAL,
            created_at TEXT,
            updated_at TEXT,
            last_accessed_at TEXT,
            status TEXT,
            supersedes_id TEXT
        )
    """)

    # insert a chain of 100 memories
    prev_id = None
    first_id = None
    for i in range(100):
        new_id = str(uuid.uuid4())
        if first_id is None:
            first_id = new_id

        cursor.execute("""
            INSERT INTO memories (id, supersedes_id) VALUES (?, ?)
        """, (new_id, prev_id))
        prev_id = new_id

    conn.commit()
    conn.close()
    return db_path, prev_id

def bench():
    db_path, last_id = setup_db()
    store = MemoryStore(db_path)

    start = time.time()
    for _ in range(100):
        store.get_superseded_chain(last_id)
    end = time.time()

    print(f"Time taken: {end - start:.4f} seconds")

if __name__ == "__main__":
    bench()
