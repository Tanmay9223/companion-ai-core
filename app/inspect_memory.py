"""Standalone script to inspect the memory database outside of a chat session.

Usage:
    python -m app.inspect_memory
"""

import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

DB_PATH = os.getenv("DB_PATH", "memory.sqlite")


def main():
    if not os.path.exists(DB_PATH):
        print(f"No database found at {DB_PATH}. Run the chat loop first.")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # --- Active memories ---
    cursor.execute("SELECT * FROM memories WHERE status = 'active' ORDER BY created_at DESC")
    active = cursor.fetchall()
    print(f"\n{'='*60}")
    print(f"  ACTIVE MEMORIES ({len(active)})")
    print(f"{'='*60}")
    for m in active:
        print(f"  [{m['memory_type']}] {m['subject']} → {m['predicate']} = {m['value']}")
        print(f"         importance={m['importance']}  created={m['created_at']}")

    # --- Superseded memories ---
    cursor.execute("SELECT * FROM memories WHERE status = 'superseded' ORDER BY updated_at DESC")
    superseded = cursor.fetchall()
    print(f"\n{'='*60}")
    print(f"  SUPERSEDED MEMORIES ({len(superseded)})")
    print(f"{'='*60}")
    for m in superseded:
        print(f"  [{m['memory_type']}] {m['subject']} → {m['predicate']} = {m['value']}")
        print(f"         superseded_at={m['updated_at']}  source=\"{m['source_text']}\"")

    # --- Expired memories ---
    cursor.execute("SELECT * FROM memories WHERE status = 'expired' ORDER BY updated_at DESC")
    expired = cursor.fetchall()
    print(f"\n{'='*60}")
    print(f"  EXPIRED MEMORIES ({len(expired)})")
    print(f"{'='*60}")
    for m in expired:
        print(f"  [{m['memory_type']}] {m['subject']} → {m['predicate']} = {m['value']}")
        print(f"         expired_at={m['updated_at']}")

    # --- Recent conversation turns ---
    try:
        cursor.execute("SELECT * FROM conversation_turns ORDER BY id DESC LIMIT 20")
        turns = cursor.fetchall()
        print(f"\n{'='*60}")
        print(f"  RECENT CONVERSATION TURNS (last {len(turns)})")
        print(f"{'='*60}")
        for t in reversed(list(turns)):
            prefix = "You" if t["role"] == "user" else "Robin"
            content_preview = t["content"][:80] + ("…" if len(t["content"]) > 80 else "")
            print(f"  [{prefix}] {content_preview}")
    except sqlite3.OperationalError:
        print("\n  (No conversation_turns table found)")

    conn.close()
    print()


if __name__ == "__main__":
    main()
