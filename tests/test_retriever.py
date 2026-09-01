import os
import sqlite3
import datetime
import pytest
from app.memory_store import MemoryStore
from app.retriever import MemoryRetriever
from app.schema import ExtractedMemory

TEST_DB = "test_retriever.sqlite"


def _create_db():
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


@pytest.fixture
def setup():
    _create_db()
    store = MemoryStore(db_path=TEST_DB)
    retriever = MemoryRetriever(db_path=TEST_DB)

    # Seed some memories
    store.insert_memory(
        ExtractedMemory(
            subject="user", predicate="employer", value="Acme Corp",
            memory_type="employment", importance=0.8, confidence=1.0,
        ),
        source_text="I work at Acme Corp",
    )
    store.insert_memory(
        ExtractedMemory(
            subject="user", predicate="favorite_color", value="blue",
            memory_type="preference", importance=0.4, confidence=1.0,
        ),
        source_text="My favorite color is blue",
    )
    store.insert_memory(
        ExtractedMemory(
            subject="user.sister", predicate="name", value="Neha",
            memory_type="relationship", importance=0.7, confidence=1.0,
        ),
        source_text="My sister Neha is visiting",
    )

    yield store, retriever

    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def test_retrieves_relevant_memory(setup):
    _, retriever = setup
    results = retriever.retrieve_relevant_memories("Where does the user work at Acme?")
    values = [r["value"] for r in results]
    assert "Acme Corp" in values


def test_does_not_retrieve_irrelevant(setup):
    _, retriever = setup
    # "sister" and "Neha" should match the relationship memory,
    # but the color preference should NOT appear since it has no keyword overlap
    # and low importance (0.4 < 0.8 threshold)
    results = retriever.retrieve_relevant_memories("How is sister Neha doing?")
    values = [r["value"] for r in results]
    assert "Neha" in values
    assert "blue" not in values


def test_retrieves_entity_by_name(setup):
    _, retriever = setup
    results = retriever.retrieve_relevant_memories("How is Neha doing?")
    values = [r["value"] for r in results]
    assert "Neha" in values


def test_respects_top_k(setup):
    _, retriever = setup
    results = retriever.retrieve_relevant_memories("Tell me everything", top_k=1)
    assert len(results) <= 1


def test_superseded_memories_not_retrieved(setup):
    store, retriever = setup
    # Supersede the employer
    store.insert_memory(
        ExtractedMemory(
            subject="user", predicate="employer", value="Globex",
            memory_type="employment", importance=0.8, confidence=1.0,
        ),
        source_text="I now work at Globex",
    )
    results = retriever.retrieve_relevant_memories("Where does the user work now?")
    values = [r["value"] for r in results]
    assert "Globex" in values
    assert "Acme Corp" not in values
