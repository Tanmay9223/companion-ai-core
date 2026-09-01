import sqlite3
import datetime
from .init_db import DB_PATH


class ConversationHistory:
    """Manages conversation turn persistence in SQLite.

    Stores recent turns for multi-turn LLM coherence and
    restores the last N turns on process restart so the companion
    retains short-term conversational context across sessions.
    """

    def __init__(self, db_path=DB_PATH, max_turns: int = 10):
        self.db_path = db_path
        self.max_turns = max_turns
        self._history: list[dict] = []
        self._load_recent_turns()

    def _load_recent_turns(self):
        """Load the most recent turns from SQLite on startup."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT role, content FROM conversation_turns ORDER BY id DESC LIMIT ?",
                (self.max_turns,),
            )
            rows = cursor.fetchall()
            # Rows come newest-first; reverse to chronological order
            self._history = [
                {"role": row["role"], "content": row["content"]}
                for row in reversed(rows)
            ]
        except sqlite3.OperationalError:
            # Table might not exist yet on first run
            self._history = []
        finally:
            conn.close()

    def add_turn(self, role: str, content: str):
        """Persist a single turn and keep the in-memory window trimmed."""
        now = datetime.datetime.now(datetime.UTC).isoformat()
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO conversation_turns (role, content, created_at) VALUES (?, ?, ?)",
            (role, content, now),
        )
        conn.commit()
        conn.close()

        self._history.append({"role": role, "content": content})
        # Keep only the most recent turns in memory
        if len(self._history) > self.max_turns:
            self._history = self._history[-self.max_turns :]

    def get_recent_turns(self) -> list[dict]:
        """Return the in-memory sliding window of recent turns."""
        return list(self._history)
