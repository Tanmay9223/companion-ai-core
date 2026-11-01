"""Standalone script to inspect the memory database outside of a chat session.

Usage:
    python -m app.inspect_memory
"""

import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "memory.sqlite")


def print_memories(cursor, status, title):
    order_col = "created_at" if status == "active" else "updated_at"
    cursor.execute(f"SELECT * FROM memories WHERE status = ? ORDER BY {order_col} DESC", (status,))
    records = cursor.fetchall()
    print(f"\n{'='*60}")
    print(f"  {title} ({len(records)})")
    print(f"{'='*60}")
    for m in records:
        print(f"  [{m['memory_type']}] {m['subject']} → {m['predicate']} = {m['value']}")
        if status == 'active':
            print(f"         importance={m['importance']}  created={m['created_at']}")
        elif status == 'superseded':
            print(f"         superseded_at={m['updated_at']}  source=\"{m['source_text']}\"")
        elif status == 'expired':
            print(f"         expired_at={m['updated_at']}")


def main():
    if not os.path.exists(DB_PATH):
        print(f"No database found at {DB_PATH}. Run the chat loop first.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # --- Active memories ---
    print_memories(cursor, 'active', 'ACTIVE MEMORIES')

    # --- Superseded memories ---
    print_memories(cursor, 'superseded', 'SUPERSEDED MEMORIES')

    # --- Expired memories ---
    print_memories(cursor, 'expired', 'EXPIRED MEMORIES')

    # --- Recent conversation turns ---
    try:
        cursor.execute("SELECT * FROM conversation_turns ORDER BY id DESC LIMIT 20")
        turns = cursor.fetchall()
        print(f"\n{'='*60}")
        print(f"  RECENT CONVERSATION TURNS (last {len(turns)})")
        print(f"{'='*60}")
        for t in reversed(list(turns)):
            prefix = "You" if t["role"] == "user" else "Syra"
            content_preview = t["content"][:80] + ("…" if len(t["content"]) > 80 else "")
            print(f"  [{prefix}] {content_preview}")
    except sqlite3.OperationalError:
        print("\n  (No conversation_turns table found)")

    conn.close()
    print()


if __name__ == "__main__":
    main()
