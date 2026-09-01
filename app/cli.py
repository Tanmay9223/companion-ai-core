import os
from .llm_adapter import LLMAdapter
from .init_db import init_db
from .extractor import MemoryExtractor
from .memory_store import MemoryStore
from .retriever import MemoryRetriever

def main():
    print("Starting Companion-AI CLI...")
    init_db()
    adapter = LLMAdapter()
    extractor = MemoryExtractor()
    store = MemoryStore()
    retriever = MemoryRetriever()
    
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
            
            # Retrieve relevant active memories
            relevant_memories = retriever.retrieve_relevant_memories(user_input)
            context_blocks = []
            if relevant_memories:
                context_blocks.append("Relevant memories about the user:")
                for m in relevant_memories:
                    context_blocks.append(f"- {m['subject']} {m['predicate']} {m['value']}")
            
            context_string = "\n".join(context_blocks)
            system_prompt = f"System: You are Robin.\n{context_string}"
            
            response = adapter.generate_response(system_prompt, user_input)
            print(f"Robin: {response}")
            
            # Extract memory (async in a real app)
            extraction = extractor.extract_memories(user_input)
            if extraction.is_memory_worthy:
                for memory in extraction.memories:
                    mem_id, status = store.insert_memory(memory, source_text=user_input)
                    print(f"[Debug] Extracted memory: {memory.subject} {memory.predicate} {memory.value} ({status})")
                    
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break

if __name__ == "__main__":
    main()
