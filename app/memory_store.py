import sqlite3
import uuid
import datetime
from .init_db import DB_PATH
from .schema import ExtractedMemory

class MemoryStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        
    def _insert_memory_record(self, cursor, memory_id: str, memory: ExtractedMemory, source_text: str, now: str, supersedes_id: str = None):
        cursor.execute("""
            INSERT INTO memories (
                id, namespace, subject, predicate, value, memory_type,
                source_text, importance, created_at, updated_at, last_accessed_at, status, supersedes_id
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            memory_id,
            "user" if memory.subject.startswith("user") else "companion",
            memory.subject, memory.predicate, memory.value, memory.memory_type,
            source_text, memory.importance, now, now, now, "active", supersedes_id
        ))

    def _insert_single_memory(self, cursor, memory: ExtractedMemory, source_text: str, now: str):
        memory_id = str(uuid.uuid4())
        
        # Phase 4: Contradiction & Duplicate Resolution
        cursor.execute(
            "SELECT id, value FROM memories WHERE subject = ? AND predicate = ? AND status = 'active'", 
            (memory.subject, memory.predicate)
        )
        existing = cursor.fetchall()
        
        if existing:
            old_mem = existing[0]
            if old_mem['value'].lower() == memory.value.lower():
                # Duplicate
                cursor.execute("UPDATE memories SET last_accessed_at = ? WHERE id = ?", (now, old_mem['id']))
                return old_mem['id'], "duplicate"
            else:
                # Contradiction / Supersede
                cursor.execute("UPDATE memories SET status = 'superseded', updated_at = ? WHERE id = ?", (now, old_mem['id']))
                self._insert_memory_record(cursor, memory_id, memory, source_text, now, supersedes_id=old_mem['id'])
                return memory_id, "superseded"
        else:
            # New memory
            self._insert_memory_record(cursor, memory_id, memory, source_text, now)
            return memory_id, "new"

    def insert_memory(self, memory: ExtractedMemory, source_text: str):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        now = datetime.datetime.utcnow().isoformat()
        
        mem_id, status = self._insert_single_memory(cursor, memory, source_text, now)

        conn.commit()
        conn.close()
        return mem_id, status

    def insert_memories(self, memories: list[ExtractedMemory], source_text: str):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        now = datetime.datetime.utcnow().isoformat()
        results = []
        for memory in memories:
            mem_id, status = self._insert_single_memory(cursor, memory, source_text, now)
            results.append((memory, mem_id, status))

        conn.commit()
        conn.close()
        return results

    def get_all_active_memories(self, subject: str = None, predicate: str = None):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM memories WHERE status = 'active'"
        params = []

        if subject is not None:
            query += " AND subject = ?"
            params.append(subject)

        if predicate is not None:
            query += " AND predicate = ?"
            params.append(predicate)

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_all_memories_with_status(self, include_superseded: bool = True):
        """Return all memories including superseded ones, for debug inspection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        if include_superseded:
            cursor.execute("SELECT * FROM memories ORDER BY created_at DESC")
        else:
            cursor.execute("SELECT * FROM memories WHERE status != 'superseded' ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]

    def get_superseded_chain(self, memory_id: str):
        """Walk the supersession chain backwards from a given memory."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            WITH RECURSIVE chain AS (
                SELECT *
                FROM memories
                WHERE id = ?
                UNION ALL
                SELECT m.*
                FROM memories m
                INNER JOIN chain c ON c.supersedes_id = m.id
            )
            SELECT * FROM chain;
        """, (memory_id,))
        rows = cursor.fetchall()
        chain = [dict(row) for row in rows]
        conn.close()
        return chain

    def decay_stale_memories(self, max_age_days: int = 30):
        """Mark stale plan/event memories as 'expired' if they are older than max_age_days.

        This implements the 'decay' requirement — plans and events that have
        passed their useful window are retired from active retrieval while
        remaining in the database for historical reference.
        """
        now = datetime.datetime.utcnow()
        cutoff = (now - datetime.timedelta(days=max_age_days)).isoformat()

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            """UPDATE memories
               SET status = 'expired', updated_at = ?
               WHERE status = 'active'
                 AND memory_type IN ('plan', 'event')
                 AND created_at < ?""",
            (now.isoformat(), cutoff),
        )
        expired_count = cursor.rowcount
        conn.commit()
        conn.close()
        return expired_count

