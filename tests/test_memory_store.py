import os
import sqlite3
import pytest
from app.memory_store import MemoryStore
from app.schema import ExtractedMemory
from app.init_db import init_db

TEST_DB = "test_memory.sqlite"

@pytest.fixture
def store():
    # Setup
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
        
    init_db(TEST_DB)
    
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

    # Test get_superseded_chain
    chain = store.get_superseded_chain(mem2_id)
    assert len(chain) == 2
    assert chain[0]['id'] == mem2_id
    assert chain[0]['value'] == "Globex"
    assert chain[1]['id'] == mem1_id
    assert chain[1]['value'] == "Acme"

    # Test get_superseded_chain with older memory
    chain_old = store.get_superseded_chain(mem1_id)
    assert len(chain_old) == 1
    assert chain_old[0]['id'] == mem1_id
    assert chain_old[0]['value'] == "Acme"

    # Test get_superseded_chain with non-existent memory
    chain_none = store.get_superseded_chain("nonexistent")
    assert len(chain_none) == 0

def test_get_all_memories_with_status(store):
    # Insert first memory
    mem1 = ExtractedMemory(
        subject="user",
        predicate="favorite_color",
        value="blue",
        memory_type="preference",
        importance=0.5,
        confidence=1.0
    )
    mem1_id, _ = store.insert_memory(mem1, "My favorite color is blue")

    # Insert a new memory to supersede the first
    mem2 = ExtractedMemory(
        subject="user",
        predicate="favorite_color",
        value="red",
        memory_type="preference",
        importance=0.6,
        confidence=1.0
    )
    mem2_id, _ = store.insert_memory(mem2, "Actually, I like red more now")

    # Insert another unrelated active memory
    mem3 = ExtractedMemory(
        subject="user",
        predicate="hobby",
        value="reading",
        memory_type="interest",
        importance=0.7,
        confidence=1.0
    )
    mem3_id, _ = store.insert_memory(mem3, "I enjoy reading books")

    # Retrieve all memories
    all_memories = store.get_all_memories_with_status()

    # We should have 3 memories in total
    assert len(all_memories) == 3

    # They should be ordered by created_at DESC (most recent first)
    assert all_memories[0]['id'] == mem3_id
    assert all_memories[1]['id'] == mem2_id
    assert all_memories[2]['id'] == mem1_id

    # Verify statuses
    assert all_memories[0]['status'] == "active"
    assert all_memories[1]['status'] == "active"
    assert all_memories[2]['status'] == "superseded"
