import os
import sqlite3
import datetime
import pytest
from app.memory_store import MemoryStore
from app.schema import ExtractedMemory

TEST_DB = "test_decay.sqlite"


@pytest.fixture
def store():
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

    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def _insert_old_memory(db_path, subject, predicate, value, memory_type, days_old):
    """Helper to insert a memory with a backdated created_at."""
    import uuid
    old_date = (datetime.datetime.utcnow() - datetime.timedelta(days=days_old)).isoformat()
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    mem_id = str(uuid.uuid4())
    cursor.execute("""
        INSERT INTO memories (
            id, namespace, subject, predicate, value, memory_type,
            source_text, importance, created_at, updated_at, last_accessed_at, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        mem_id, "user", subject, predicate, value, memory_type,
        "test", 0.5, old_date, old_date, old_date, "active",
    ))
    conn.commit()
    conn.close()
    return mem_id


def test_decay_expires_old_plans(store):
    # Insert a plan from 60 days ago
    _insert_old_memory(TEST_DB, "user", "interview", "Acme next Thursday", "plan", 60)
    # Insert a recent plan
    store.insert_memory(
        ExtractedMemory(
            subject="user", predicate="trip", value="Paris next month",
            memory_type="plan", importance=0.6, confidence=1.0,
        ),
        source_text="Going to Paris next month",
    )

    expired = store.decay_stale_memories(max_age_days=30)
    assert expired == 1  # Only the 60-day-old plan

    active = store.get_all_active_memories()
    assert len(active) == 1
    assert active[0]["value"] == "Paris next month"


def test_decay_does_not_expire_identity_facts(store):
    # Identity facts should never decay even if old
    _insert_old_memory(TEST_DB, "user", "name", "Tanmay", "identity", 90)

    expired = store.decay_stale_memories(max_age_days=30)
    assert expired == 0

    active = store.get_all_active_memories()
    assert len(active) == 1
