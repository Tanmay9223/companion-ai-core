import os
from dotenv import load_dotenv
from openai import OpenAI
from .schema import ExtractionResult, ExtractedMemory

load_dotenv()


class MemoryExtractor:
    """Extracts structured, durable facts from user messages using an LLM.

    Uses OpenAI's structured outputs (response_format) to guarantee
    the output conforms to the ExtractionResult Pydantic schema.
    """

    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        if self.api_key:
            self.client = OpenAI(api_key=self.api_key)
        else:
            self.client = None

    def extract_memories(self, user_message: str) -> ExtractionResult:
        if not self.client:
            print("[Mock Extractor] No OPENAI_API_KEY found. Skipping extraction.")
            return ExtractionResult(is_memory_worthy=False, memories=[])

        prompt = f"""You are a memory extraction component for a conversational AI companion.

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
    {{subject: "user", predicate: "employer", value: "Google", memory_type: "employment", importance: 0.9, confidence: 1.0}},
    {{subject: "user", predicate: "job_title", value: "software engineer", memory_type: "employment", importance: 0.7, confidence: 1.0}}
  ]

User: "My sister Neha is visiting me next weekend."
→ is_memory_worthy: true
→ memories: [
    {{subject: "user.sister.Neha", predicate: "plan", value: "visiting user next weekend", memory_type: "plan", importance: 0.7, confidence: 1.0}}
  ]

User: "Maya and I broke up last week."
→ is_memory_worthy: true
→ memories: [
    {{subject: "user", predicate: "relationship_status", value: "single (broke up with Maya)", memory_type: "relationship", importance: 0.9, confidence: 1.0}}
  ]

User: "Haha yeah that's funny"
→ is_memory_worthy: false
→ memories: []

User: "I've been really into rock climbing lately."
→ is_memory_worthy: true
→ memories: [
    {{subject: "user", predicate: "hobby", value: "rock climbing", memory_type: "preference", importance: 0.6, confidence: 0.8}}
  ]

NOW EXTRACT FROM THIS MESSAGE:

User: "{user_message}"
"""

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
