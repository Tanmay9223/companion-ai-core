import os
import sqlite3
import pytest
from app.init_db import init_db
from app.memory_store import MemoryStore
from app.schema import ExtractedMemory

TEST_DB = "test_memory.sqlite"

@pytest.fixture
def store():
    # Setup
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
        
    conn = sqlite3.connect(TEST_DB)
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
    
    yield MemoryStore(db_path=TEST_DB)
    
    # Teardown
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)

def test_insert_new_memory(store):
    mem = ExtractedMemory(
        subject="user.sister",
        predicate="name",
        value="Neha",
        memory_type="relationship",
        importance=0.8,
        confidence=1.0
    )
    mem_id, status = store.insert_memory(mem, "My sister's name is Neha")
    assert status == "new"
    
    active = store.get_all_active_memories()
    assert len(active) == 1
    assert active[0]['value'] == "Neha"

def test_duplicate_memory(store):
    mem = ExtractedMemory(
        subject="user.sister",
        predicate="name",
        value="Neha",
        memory_type="relationship",
        importance=0.8,
        confidence=1.0
    )
    store.insert_memory(mem, "My sister's name is Neha")
    
    mem_id, status = store.insert_memory(mem, "Like I said, my sister is Neha")
    assert status == "duplicate"
    
    active = store.get_all_active_memories()
    assert len(active) == 1

def test_contradiction_supersession(store):
    mem1 = ExtractedMemory(
        subject="user",
        predicate="employer",
        value="Acme",
        memory_type="employment",
        importance=0.8,
        confidence=1.0
    )
    mem1_id, _ = store.insert_memory(mem1, "I work at Acme")
    
    mem2 = ExtractedMemory(
        subject="user",
        predicate="employer",
        value="Globex",
        memory_type="employment",
        importance=0.8,
        confidence=1.0
    )
    mem2_id, status = store.insert_memory(mem2, "I quit and now work at Globex")
    assert status == "superseded"
    
    active = store.get_all_active_memories()
    assert len(active) == 1
    assert active[0]['value'] == "Globex"
    assert active[0]['supersedes_id'] == mem1_id
    
    # Check historical status of first memory
    conn = sqlite3.connect(TEST_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT status FROM memories WHERE id = ?", (mem1_id,))
    old_status = cursor.fetchone()['status']
    conn.close()
    
    assert old_status == "superseded"
