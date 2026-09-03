import os
import json
from dotenv import load_dotenv
from .schema import ExtractionResult, ExtractedMemory

load_dotenv()

EXTRACTION_PROMPT = """You are a memory extraction component for a conversational AI companion.

TASK: Analyze the user's message and extract durable, long-term facts worth remembering.

RULES:
- Extract ONLY personal durable facts: identity, relationships, employment, preferences, plans, goals, events.
- Do NOT extract casual conversation, greetings, or temporary states (e.g., "I am drinking water", "lol", "how are you").
- Normalize entities consistently:
  - "I" / "me" → subject: "user"
  - "my mom" / "my mother" → subject: "user.mother"
  - "my sister Neha" → subject: "user.sister.Neha"
  - "my boyfriend Jake" → subject: "user.boyfriend.Jake"
- Use consistent, simple predicate names:
  - employer, job_title, relationship_status, name, age, city, hobby, preference, plan, goal, opinion
- For contradictions/updates (e.g., "I quit my job", "we broke up"), still extract the NEW state as a fact.

FEW-SHOT EXAMPLES:

User: "I just started working at Google as a software engineer."
→ is_memory_worthy: true
→ memories: [
    {{"subject": "user", "predicate": "employer", "value": "Google", "memory_type": "employment", "importance": 0.9, "confidence": 1.0}},
    {{"subject": "user", "predicate": "job_title", "value": "software engineer", "memory_type": "employment", "importance": 0.7, "confidence": 1.0}}
  ]

User: "My sister Neha is visiting me next weekend."
→ is_memory_worthy: true
→ memories: [
    {{"subject": "user.sister.Neha", "predicate": "plan", "value": "visiting user next weekend", "memory_type": "plan", "importance": 0.7, "confidence": 1.0}}
  ]

User: "Maya and I broke up last week."
→ is_memory_worthy: true
→ memories: [
    {{"subject": "user", "predicate": "relationship_status", "value": "single (broke up with Maya)", "memory_type": "relationship", "importance": 0.9, "confidence": 1.0}}
  ]

User: "Haha yeah that's funny"
→ is_memory_worthy: false
→ memories: []

User: "I've been really into rock climbing lately."
→ is_memory_worthy: true
→ memories: [
    {{"subject": "user", "predicate": "hobby", "value": "rock climbing", "memory_type": "preference", "importance": 0.6, "confidence": 0.8}}
  ]

NOW EXTRACT FROM THIS MESSAGE:

User: "{user_message}"

Respond with ONLY valid JSON in this exact format:
{{
  "is_memory_worthy": true/false,
  "memories": [
    {{"subject": "...", "predicate": "...", "value": "...", "memory_type": "...", "importance": 0.0-1.0, "confidence": 0.0-1.0}}
  ]
}}"""


class MemoryExtractor:
    """Extracts structured, durable facts from user messages using an LLM.

    Supports OpenAI (structured outputs) and Google Gemini (JSON mode).
    """

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
            self.model = os.getenv("LLM_MODEL", "gpt-4.1-mini")
            api_key = os.getenv("OPENAI_API_KEY")
            if api_key:
                from openai import OpenAI
                self.client = OpenAI(api_key=api_key)

    def extract_memories(self, user_message: str) -> ExtractionResult:
        if not self.client:
            print("[Mock Extractor] No API key found. Skipping extraction.")
            return ExtractionResult(is_memory_worthy=False, memories=[])

        prompt = EXTRACTION_PROMPT.format(user_message=user_message)

        if self.provider == "gemini":
            return self._extract_gemini(prompt)
        else:
            return self._extract_openai(prompt)

    def _extract_openai(self, prompt: str) -> ExtractionResult:
        """Extract using OpenAI structured outputs."""
        try:
            response = self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                response_format=ExtractionResult,
            )
            return response.choices[0].message.parsed
        except Exception as e:
            print(f"[Extractor Error] {e}")
            return ExtractionResult(is_memory_worthy=False, memories=[])

    def _extract_gemini(self, prompt: str) -> ExtractionResult:
        """Extract using Google Gemini with JSON response parsing."""
        import re
        from google.genai import types

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=prompt)],
                )],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.3,
                ),
            )
            raw = response.text.strip()
            # Strip markdown code fences if present
            raw = re.sub(r"```json\s*|\s*```", "", raw).strip()
            data = json.loads(raw)

            memories = []
            for m in data.get("memories", []):
                memories.append(ExtractedMemory(
                    subject=m["subject"],
                    predicate=m["predicate"],
                    value=m["value"],
                    memory_type=m.get("memory_type", "identity"),
                    importance=float(m.get("importance", 0.5)),
                    confidence=float(m.get("confidence", 0.8)),
                ))
            return ExtractionResult(
                is_memory_worthy=data.get("is_memory_worthy", False),
                memories=memories,
            )
        except Exception as e:
            print(f"[Extractor Error] {e}")
            return ExtractionResult(is_memory_worthy=False, memories=[])
