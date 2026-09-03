import os
import logging
from .llm_adapter import LLMAdapter
from .init_db import init_db
from .extractor import MemoryExtractor
from .memory_store import MemoryStore
from .retriever import MemoryRetriever
from .persona_manager import PersonaManager
from .conversation_history import ConversationHistory

# Configure file logging for debugging behind the scenes
logging.basicConfig(
    filename='companion.log',
    filemode='a',
    format='%(asctime)s - %(levelname)s - %(message)s',
    level=logging.INFO
)


def print_help():
    print("--- Commands ---")
    print("  /memories   Show all active memories")
    print("  /history    Show all memories including superseded/expired")
    print("  /debug      Toggle debug mode (shows injected context)")
    print("  /exit       Quit the application")
    print("----------------")


def main():
    print("Starting Companion-AI CLI...")
    init_db()

    adapter = LLMAdapter()
    extractor = MemoryExtractor()
    store = MemoryStore()
    retriever = MemoryRetriever()
    persona = PersonaManager()
    history = ConversationHistory()

    # Run memory decay on startup to retire stale plans/events
    expired = store.decay_stale_memories()
    if expired > 0:
        print(f"[Decay] Expired {expired} stale plan/event memories.")

    debug_mode = False

    print("Welcome to Companion-AI! Type /exit to quit.")
    print("Type /memories, /history, /debug, or /exit.")

    # Show if there is prior context
    recent = history.get_recent_turns()
    if recent:
        print(f"[Session] Restored {len(recent)} prior conversation turns.")

    print()
    logging.info("=== New CLI Session Started ===")

    while True:
        try:
            user_input = input("You: ").strip()
            if not user_input:
                continue

            # --- Handle slash commands ---
            if user_input == "/exit":
                print("Goodbye!")
                logging.info("Session ended by user.")
                break

            if user_input == "/memories":
                memories = store.get_all_active_memories()
                if not memories:
                    print("  (no active memories)")
                else:
                    print("--- Active Memories ---")
                    for m in memories:
                        print(
                            f"  [{m['memory_type']}] {m['subject']} → {m['predicate']} = {m['value']}"
                        )
                    print(f"  ({len(memories)} total)")
                    print("-----------------------")
                continue

            if user_input == "/history":
                all_mems = store.get_all_memories_with_status()
                if not all_mems:
                    print("  (no memories)")
                else:
                    print("--- All Memories (including superseded/expired) ---")
                    for m in all_mems:
                        status_icon = {
                            "active": "●",
                            "superseded": "○",
                            "expired": "✗",
                        }.get(m["status"], "?")
                        supersedes = (
                            f" (supersedes {m['supersedes_id'][:8]}…)"
                            if m.get("supersedes_id")
                            else ""
                        )
                        print(
                            f"  {status_icon} [{m['status']}] {m['subject']} → {m['predicate']} = {m['value']}{supersedes}"
                        )
                    print(f"  ({len(all_mems)} total)")
                    print("---------------------------------------------------")
                continue

            if user_input == "/debug":
                debug_mode = not debug_mode
                print(f"  Debug mode: {'ON' if debug_mode else 'OFF'}")
                continue

            if user_input.startswith("/"):
                print_help()
                continue

            # --- Core loop ---

            # 1. Retrieve relevant active memories
            relevant_memories = retriever.retrieve_relevant_memories(user_input, top_k=5)
            logging.info(f"User Input: {user_input}")
            logging.info(f"Retrieved Memories: {relevant_memories}")

            # 2. Build system prompt: persona + retrieved memories with provenance
            context_blocks = [persona.get_system_prompt_header()]
            if relevant_memories:
                context_blocks.append("\nRELEVANT MEMORIES ABOUT THE USER (use these to inform your response):")
                context_blocks.append("When recalling a fact, naturally reference it (e.g., 'I remember you mentioned...')")
                context_blocks.append("Do NOT fabricate memories — only reference facts listed below.\n")
                for m in relevant_memories:
                    source = m.get('source_text', '')
                    source_note = f' (from: "{source}")' if source else ''
                    context_blocks.append(
                        f"- {m['subject']} {m['predicate']}: {m['value']}{source_note}"
                    )

            system_prompt = "\n".join(context_blocks)
            logging.info(f"Constructed System Prompt Length: {len(system_prompt)}")

            if debug_mode:
                print(f"\n[Debug] System prompt ({len(system_prompt)} chars):")
                print(f"  Retrieved {len(relevant_memories)} memories")
                for m in relevant_memories:
                    print(
                        f"    → {m['subject']} {m['predicate']} = {m['value']}"
                    )
                print()

            # 3. Generate response with conversation history
            recent_turns = history.get_recent_turns()
            print("[Syra is typing...]")
            response = adapter.generate_response(
                system_prompt, user_input, history=recent_turns
            )
            logging.info(f"Syra Response: {response}")
            print(f"\nSyra: {response}\n")

            # 4. Persist conversation turns
            history.add_turn("user", user_input)
            history.add_turn("assistant", response)

            # 5. Extract memories from user input
            print("[Saving to memory...]")
            extraction = extractor.extract_memories(user_input)
            logging.info(f"Extraction Result: {extraction}")
            if extraction.is_memory_worthy:
                for memory in extraction.memories:
                    mem_id, status = store.insert_memory(
                        memory, source_text=user_input
                    )
                    if debug_mode:
                        print(
                            f"[Debug] Memory: {memory.subject} {memory.predicate} = {memory.value} ({status})"
                        )

        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break


if __name__ == "__main__":
    main()
