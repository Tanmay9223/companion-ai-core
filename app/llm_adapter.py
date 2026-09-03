import os
import json
from dotenv import load_dotenv

load_dotenv()


class LLMAdapter:
    """Abstraction layer for LLM API calls. Supports OpenAI and Google Gemini."""

    def __init__(self):
        self.provider = os.getenv("LLM_PROVIDER", "openai").lower()
        self.client = None

        if self.provider == "gemini":
            self.model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
            api_key = os.getenv("GOOGLE_API_KEY")
            if api_key:
                from google import genai
                self.client = genai.Client(api_key=api_key)
            else:
                print("[Warning] No GOOGLE_API_KEY found. LLM responses will be mocked.")
        else:
            self.model = os.getenv("LLM_MODEL", "gpt-4.1-mini")
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                from openai import OpenAI
                self.client = OpenAI(api_key=api_key)
            else:
                print("[Warning] No OPENAI_API_KEY found. LLM responses will be mocked.")

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

        if self.provider == "gemini":
            return self._gemini_response(system_prompt, user_message, history)
        else:
            return self._openai_response(system_prompt, user_message, history)

    def _openai_response(self, system_prompt, user_message, history):
        """Generate response via OpenAI API."""
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history)
        messages.append({"role": "user", "content": user_message})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.8,
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"[LLM Error] {e}")
            return "I'm having trouble thinking right now. Could you try again?"

    def _gemini_response(self, system_prompt, user_message, history):
        """Generate response via Google Gemini API."""
        from google.genai import types

        # Build conversation contents
        contents = []
        if history:
            for turn in history:
                role = "user" if turn["role"] == "user" else "model"
                contents.append(types.Content(
                    role=role,
                    parts=[types.Part.from_text(text=turn["content"])],
                ))
        contents.append(types.Content(
            role="user",
            parts=[types.Part.from_text(text=user_message)],
        ))

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.8,
                ),
            )
            return response.text.strip()
        except Exception as e:
            print(f"[LLM Error] {e}")
            return "I'm having trouble thinking right now. Could you try again?"
