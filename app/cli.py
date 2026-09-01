import os
from .llm_adapter import LLMAdapter
from .init_db import init_db

def main():
    print("Starting Companion-AI CLI...")
    init_db()
    adapter = LLMAdapter()
    print("Welcome to Companion-AI! Type /exit to quit.")
    
    while True:
        try:
            user_input = input("User: ")
            if user_input.strip() == "/exit":
                break
            
            response = adapter.generate_response("System: You are Robin.", user_input)
            print(f"Robin: {response}")
        except (KeyboardInterrupt, EOFError):
            print("\nExiting...")
            break

if __name__ == "__main__":
    main()
