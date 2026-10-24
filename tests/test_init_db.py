import os
import sqlite3
import pytest
import app.init_db

@pytest.fixture
def temp_db_path(tmp_path):
    """Fixture to provide a temporary database path."""
    return str(tmp_path / "test_init.sqlite")

def test_init_db_creates_tables(temp_db_path, monkeypatch):
    """Test that init_db creates the expected tables."""
    # Monkeypatch the DB_PATH to use our temporary file
    monkeypatch.setattr(app.init_db, "DB_PATH", temp_db_path)

    # Call the initialization function
    app.init_db.init_db()

    # Verify the database file was created
    assert os.path.exists(temp_db_path)

    # Connect and verify tables exist
    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()

    # Check for 'memories' table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='memories';")
    assert cursor.fetchone() is not None, "Table 'memories' was not created."

    # Check for 'conversation_turns' table
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='conversation_turns';")
    assert cursor.fetchone() is not None, "Table 'conversation_turns' was not created."

    # Check columns in memories table to ensure schema was applied
    cursor.execute("PRAGMA table_info(memories);")
    columns = {row[1] for row in cursor.fetchall()}
    expected_columns = {
        'id', 'namespace', 'subject', 'predicate', 'value', 'memory_type',
        'source_text', 'importance', 'created_at', 'updated_at',
        'last_accessed_at', 'status', 'supersedes_id', 'metadata'
    }
    assert expected_columns.issubset(columns), "Missing columns in 'memories' table."

    conn.close()

def test_init_db_idempotent(temp_db_path, monkeypatch):
    """Test that init_db can be called multiple times without errors."""
    monkeypatch.setattr(app.init_db, "DB_PATH", temp_db_path)

    # Call first time
    app.init_db.init_db()

    # Call second time (should not throw an exception)
    try:
        app.init_db.init_db()
    except Exception as e:
        pytest.fail(f"Second call to init_db failed with: {e}")

    # Verify tables still exist
    conn = sqlite3.connect(temp_db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = {row[0] for row in cursor.fetchall()}

    assert 'memories' in tables
    assert 'conversation_turns' in tables

    conn.close()
