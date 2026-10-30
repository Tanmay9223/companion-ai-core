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

def original_get_chain(store, memory_id):
    conn = sqlite3.connect(store.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    chain = []
    current_id = memory_id
    while current_id:
        cursor.execute("SELECT * FROM memories WHERE id = ?", (current_id,))
        row = cursor.fetchone()
        if row:
            mem = dict(row)
            chain.append(mem)
            current_id = mem.get("supersedes_id")
        else:
            break
    conn.close()
    return chain

def optimized_get_chain(store, memory_id):
    conn = sqlite3.connect(store.db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("""
        WITH RECURSIVE chain AS (
            SELECT *
            FROM memories
            WHERE id = ?
            UNION ALL
            SELECT m.*
            FROM memories m
            INNER JOIN chain c ON c.supersedes_id = m.id
        )
        SELECT * FROM chain;
    """, (memory_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]

def bench():
    db_path, last_id = setup_db()
    store = MemoryStore(db_path)

    start = time.time()
    for _ in range(100):
        chain1 = original_get_chain(store, last_id)
    end = time.time()
    print(f"Original time: {end - start:.4f} seconds")

    start = time.time()
    for _ in range(100):
        chain2 = optimized_get_chain(store, last_id)
    end = time.time()
    print(f"Optimized time: {end - start:.4f} seconds")

    assert len(chain1) == len(chain2)
    assert chain1 == chain2

if __name__ == "__main__":
    bench()
