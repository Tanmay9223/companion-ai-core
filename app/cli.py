import os
from .llm_adapter import LLMAdapter
from .init_db import init_db
from .extractor import MemoryExtractor
from .memory_store import MemoryStore

def main():
    print("Starting Companion-AI CLI...")
    init_db()
    adapter = LLMAdapter()
    extractor = MemoryExtractor()
    store = MemoryStore()
    
    print("Welcome to Companion-AI! Type /exit to quit.")
    print("Type /memories to see current active memories.")
    
    while True:
        try:
            user_input = input("User: ")
            if user_input.strip() == "/exit":
                break
            if user_input.strip() == "/memories":
                memories = store.get_all_active_memories()
                print("--- Active Memories ---")
                for m in memories:
                    print(f"[{m['memory_type']}] {m['subject']} -> {m['predicate']} = {m['value']}")
                print("-----------------------")
                continue
            
            response = adapter.generate_response("System: You are Robin.", user_input)
            print(f"Robin: {response}")
            
            # Extract memory (async in a real app)
            extraction = extractor.extract_memories(user_input)
            if extraction.is_memory_worthy:
                for memory in extraction.memories:
                    store.insert_memory(memory, source_text=user_input)
                    print(f"[Debug] Extracted memory: {memory.subject} {memory.predicate} {memory.value}")
                    
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break

if __name__ == "__main__":
    main()
