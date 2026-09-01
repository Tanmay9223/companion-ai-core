import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


class LLMAdapter:
    """Abstraction layer for LLM API calls. Currently supports OpenAI."""

    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "openai")
        self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self.api_key = os.getenv("OPENAI_API_KEY")

        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None
            print(
                "[Warning] No OPENAI_API_KEY found. LLM responses will be mocked."
            )

    def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        history: list = None,
    ) -> str:
        """Generate a companion response using the configured LLM.

        Args:
            system_prompt: The full system prompt including persona + retrieved memories.
            user_message: The current user input.
            history: List of {"role": ..., "content": ...} dicts for recent conversation turns.

        Returns:
            The companion's response text.
        """
        if not self.client:
            return f"[Mock] {user_message}"

        messages = [{"role": "system", "content": system_prompt}]

        # Inject recent conversation history for multi-turn coherence
        if history:
            messages.extend(history)

        messages.append({"role": "user", "content": user_message})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.8,
                max_tokens=512,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[LLM Error] {e}")
            return "I'm having trouble thinking right now. Could you try again?"
