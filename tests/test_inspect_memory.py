import pytest
from unittest.mock import patch, MagicMock
import os
import sqlite3
from app.inspect_memory import main, print_memories, DB_PATH

@patch('app.inspect_memory.os.path.exists')
@patch('builtins.print')
def test_main_no_db(mock_print, mock_exists):
    mock_exists.return_value = False

    main()

    mock_exists.assert_called_once_with(DB_PATH)
    mock_print.assert_called_once_with(f"No database found at {DB_PATH}. Run the chat loop first.")


@patch('builtins.print')
def test_print_memories_active(mock_print):
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        {
            'memory_type': 'fact',
            'subject': 'user',
            'predicate': 'name',
            'value': 'Alice',
            'importance': 0.8,
            'created_at': '2023-01-01 12:00:00'
        }
    ]

    print_memories(mock_cursor, 'active', 'ACTIVE MEMORIES')

    mock_cursor.execute.assert_called_once_with("SELECT * FROM memories WHERE status = ? ORDER BY created_at DESC", ('active',))
    mock_print.assert_any_call("  ACTIVE MEMORIES (1)")
    mock_print.assert_any_call("  [fact] user → name = Alice")
    mock_print.assert_any_call("         importance=0.8  created=2023-01-01 12:00:00")


@patch('builtins.print')
def test_print_memories_superseded(mock_print):
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        {
            'memory_type': 'fact',
            'subject': 'user',
            'predicate': 'city',
            'value': 'New York',
            'updated_at': '2023-02-01 12:00:00',
            'source_text': 'I live in NYC'
        }
    ]

    print_memories(mock_cursor, 'superseded', 'SUPERSEDED MEMORIES')

    mock_cursor.execute.assert_called_once_with("SELECT * FROM memories WHERE status = ? ORDER BY updated_at DESC", ('superseded',))
    mock_print.assert_any_call("  SUPERSEDED MEMORIES (1)")
    mock_print.assert_any_call("  [fact] user → city = New York")
    mock_print.assert_any_call('         superseded_at=2023-02-01 12:00:00  source="I live in NYC"')


@patch('builtins.print')
def test_print_memories_expired(mock_print):
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [
        {
            'memory_type': 'plan',
            'subject': 'user',
            'predicate': 'activity',
            'value': 'meeting',
            'updated_at': '2023-03-01 12:00:00'
        }
    ]

    print_memories(mock_cursor, 'expired', 'EXPIRED MEMORIES')

    mock_cursor.execute.assert_called_once_with("SELECT * FROM memories WHERE status = ? ORDER BY updated_at DESC", ('expired',))
    mock_print.assert_any_call("  EXPIRED MEMORIES (1)")
    mock_print.assert_any_call("  [plan] user → activity = meeting")
    mock_print.assert_any_call("         expired_at=2023-03-01 12:00:00")


@patch('app.inspect_memory.os.path.exists')
@patch('app.inspect_memory.sqlite3.connect')
@patch('app.inspect_memory.print_memories')
@patch('builtins.print')
def test_main_with_db(mock_print, mock_print_memories, mock_connect, mock_exists):
    mock_exists.return_value = True

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    mock_cursor.fetchall.return_value = [
        {
            'id': 2,
            'role': 'assistant',
            'content': 'Hello, Alice! A long message that gets truncated hopefully because it is over eighty characters long...'
        },
        {
            'id': 1,
            'role': 'user',
            'content': 'Hi, Syra'
        }
    ]

    main()

    mock_exists.assert_called_once_with(DB_PATH)
    mock_connect.assert_called_once_with(DB_PATH)

    assert mock_print_memories.call_count == 3
    mock_print_memories.assert_any_call(mock_cursor, 'active', 'ACTIVE MEMORIES')
    mock_print_memories.assert_any_call(mock_cursor, 'superseded', 'SUPERSEDED MEMORIES')
    mock_print_memories.assert_any_call(mock_cursor, 'expired', 'EXPIRED MEMORIES')

    mock_cursor.execute.assert_called_once_with("SELECT * FROM conversation_turns ORDER BY id DESC LIMIT 20")

    mock_print.assert_any_call("  RECENT CONVERSATION TURNS (last 2)")
    mock_print.assert_any_call("  [You] Hi, Syra")
    mock_print.assert_any_call("  [Syra] Hello, Alice! A long message that gets truncated hopefully because it is over ei…")

    mock_conn.close.assert_called_once()


@patch('app.inspect_memory.os.path.exists')
@patch('app.inspect_memory.sqlite3.connect')
@patch('app.inspect_memory.print_memories')
@patch('builtins.print')
def test_main_no_conversation_turns_table(mock_print, mock_print_memories, mock_connect, mock_exists):
    mock_exists.return_value = True

    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_connect.return_value = mock_conn
    mock_conn.cursor.return_value = mock_cursor

    mock_cursor.execute.side_effect = sqlite3.OperationalError("no such table: conversation_turns")

    main()

    mock_exists.assert_called_once_with(DB_PATH)
    mock_connect.assert_called_once_with(DB_PATH)

    mock_cursor.execute.assert_called_once_with("SELECT * FROM conversation_turns ORDER BY id DESC LIMIT 20")

    mock_print.assert_any_call("\n  (No conversation_turns table found)")

    mock_conn.close.assert_called_once()
