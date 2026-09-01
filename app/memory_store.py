import sqlite3
import uuid
import datetime
from .init_db import DB_PATH
from .schema import ExtractedMemory

class MemoryStore:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        
    def insert_memory(self, memory: ExtractedMemory, source_text: str):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        now = datetime.datetime.utcnow().isoformat()
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
                conn.commit()
                conn.close()
                return old_mem['id'], "duplicate"
            else:
                # Contradiction / Supersede
                cursor.execute("UPDATE memories SET status = 'superseded', updated_at = ? WHERE id = ?", (now, old_mem['id']))
                cursor.execute("""
                    INSERT INTO memories (
                        id, namespace, subject, predicate, value, memory_type, 
                        source_text, importance, created_at, updated_at, last_accessed_at, status, supersedes_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    memory_id,
                    "user" if memory.subject.startswith("user") else "companion",
                    memory.subject, memory.predicate, memory.value, memory.memory_type,
                    source_text, memory.importance, now, now, now, "active", old_mem['id']
                ))
                conn.commit()
                conn.close()
                return memory_id, "superseded"
        else:
            # New memory
            cursor.execute("""
                INSERT INTO memories (
                    id, namespace, subject, predicate, value, memory_type, 
                    source_text, importance, created_at, updated_at, last_accessed_at, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory_id,
                "user" if memory.subject.startswith("user") else "companion",
                memory.subject, memory.predicate, memory.value, memory.memory_type,
                source_text, memory.importance, now, now, now, "active"
            ))
            
            conn.commit()
            conn.close()
            return memory_id, "new"
        
    def get_all_active_memories(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM memories WHERE status = 'active'")
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
