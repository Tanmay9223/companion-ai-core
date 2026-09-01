import os
from openai import OpenAI
from .schema import ExtractionResult, ExtractedMemory

class MemoryExtractor:
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None
            
    def extract_memories(self, user_message: str) -> ExtractionResult:
        if not self.client:
            # Mock behavior if no API key is provided
            print("[Mock Extractor] No OPENAI_API_KEY found. Skipping actual LLM extraction.")
            return ExtractionResult(is_memory_worthy=False, memories=[])
            
        prompt = f"""You are a memory extraction component for a conversational AI companion.
Your job is to analyze the user's message and extract durable, long-term facts.
Do not extract casual conversation or temporary states (e.g., "I am drinking water").
Extract core identity facts, relationships, preferences, plans, and events.
Normalize entities: 'my mom' -> 'user.mother', 'I' -> 'user'.

User Message: {user_message}"""

        response = self.client.beta.chat.completions.parse(
            model="gpt-4o-2024-08-06",
            messages=[{"role": "user", "content": prompt}],
            response_format=ExtractionResult
        )
        return response.choices[0].message.parsed
