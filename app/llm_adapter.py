import os
from dotenv import load_dotenv

load_dotenv()

class LLMAdapter:
    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "openai")
        
    def generate_response(self, system_prompt: str, user_message: str, history: list = None) -> str:
        # Mock response for Phase 1 skeleton
        return f"Echoing from {self.provider}: {user_message}"
