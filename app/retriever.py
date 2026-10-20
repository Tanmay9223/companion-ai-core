import sqlite3
from .init_db import DB_PATH

class MemoryRetriever:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        
    def retrieve_relevant_memories(self, query: str, top_k: int = 3):
        # MVP Retrieval Strategy: Keyword matching + importance + recency
        keywords = set(word.lower() for word in query.split() if len(word) > 3)
        
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute("SELECT *, CAST(julianday('now') - julianday(last_accessed_at) AS INTEGER) as days_old FROM memories WHERE status = 'active'")
        rows = cursor.fetchall()
        conn.close()
        
        scored_memories = []
        
        for row in rows:
            memory = dict(row)
            # Keyword score — search across all textual fields
            text_to_search = (
                f"{memory['subject']} {memory['predicate']} {memory['value']} "
                f"{memory.get('source_text', '')} {memory.get('memory_type', '')}"
            ).lower()
            keyword_score = sum(1 for kw in keywords if kw in text_to_search) * 1.5
            
            # Recency penalty
            days_old = memory.get('days_old')
            if days_old is not None:
                # use max(0, days_old) just in case
                days_old = max(0, days_old)
                recency_penalty = min(days_old * 0.05, 0.5)
            else:
                recency_penalty = 0.0
                
            # Importance weight
            importance = memory.get('importance', 0.5)
            
            final_score = keyword_score + importance - recency_penalty
            
            # Require at least some keyword overlap unless it's a critical identity fact
            if keyword_score > 0 or importance > 0.8:
                scored_memories.append((final_score, memory))
                
        # Sort descending by score
        scored_memories.sort(key=lambda x: x[0], reverse=True)
        return [m[1] for m in scored_memories[:top_k]]
