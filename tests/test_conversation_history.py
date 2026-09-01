import os
import sqlite3
import pytest
from app.conversation_history import ConversationHistory

TEST_DB = "test_history.sqlite"


@pytest.fixture
def hist():
    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)
    conn = sqlite3.connect(TEST_DB)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS conversation_turns (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        created_at DATETIME NOT NULL
    );
    """)
    conn.commit()
    conn.close()

    yield ConversationHistory(db_path=TEST_DB, max_turns=5)

    if os.path.exists(TEST_DB):
        os.remove(TEST_DB)


def test_add_and_retrieve_turns(hist):
    hist.add_turn("user", "Hello")
    hist.add_turn("assistant", "Hi there!")
    turns = hist.get_recent_turns()
    assert len(turns) == 2
    assert turns[0]["role"] == "user"
    assert turns[1]["content"] == "Hi there!"


def test_persistence_across_instances(hist):
    hist.add_turn("user", "Remember this")
    hist.add_turn("assistant", "I will!")

    # Create a new instance pointing at the same DB — simulates a restart
    hist2 = ConversationHistory(db_path=TEST_DB, max_turns=5)
    turns = hist2.get_recent_turns()
    assert len(turns) == 2
    assert turns[0]["content"] == "Remember this"


def test_max_turns_trimming(hist):
    for i in range(10):
        hist.add_turn("user", f"Message {i}")

    turns = hist.get_recent_turns()
    assert len(turns) == 5
    # Should have the 5 most recent
    assert turns[0]["content"] == "Message 5"
    assert turns[4]["content"] == "Message 9"
