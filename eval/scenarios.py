"""Synthetic test conversation set for evaluating the memory system.

Each scenario is a list of turns with assertions about expected memory state
after execution. These are designed to exercise:
  1. Basic memory recall
  2. Contradiction handling / supersession
  3. Long-range consistency (state a fact, revisit many turns later)
  4. Persona consistency (try to make the companion break character)
  5. Duplicate detection (restate the same fact)

The scenarios are deterministic — they don't call the LLM for extraction.
Instead they directly drive the MemoryStore and MemoryRetriever to test
the core memory engine, which is what the assignment focuses on.
"""

SCENARIOS = [
    # ─── Scenario 1: Basic fact insertion and recall ─────────────────────
    {
        "name": "Basic Fact Insertion and Recall",
        "description": "State a fact, verify it is stored and retrievable.",
        "steps": [
            {
                "action": "insert",
                "memory": {
                    "subject": "user",
                    "predicate": "employer",
                    "value": "Acme Corp",
                    "memory_type": "employment",
                    "importance": 0.9,
                    "confidence": 1.0,
                },
                "source_text": "I work at Acme Corp as a backend engineer.",
            },
            {
                "action": "assert_active",
                "expected": {"subject": "user", "predicate": "employer", "value": "Acme Corp"},
            },
            {
                "action": "assert_retrieval",
                "query": "Where does the user work?",
                "expected_values": ["Acme Corp"],
            },
        ],
    },
    # ─── Scenario 2: Contradiction / supersession ────────────────────────
    {
        "name": "Contradiction Supersession",
        "description": "State a fact, then contradict it. Old fact should be superseded.",
        "steps": [
            {
                "action": "insert",
                "memory": {
                    "subject": "user",
                    "predicate": "employer",
                    "value": "Acme Corp",
                    "memory_type": "employment",
                    "importance": 0.9,
                    "confidence": 1.0,
                },
                "source_text": "I work at Acme Corp.",
            },
            {
                "action": "insert",
                "memory": {
                    "subject": "user",
                    "predicate": "employer",
                    "value": "Google",
                    "memory_type": "employment",
                    "importance": 0.9,
                    "confidence": 1.0,
                },
                "source_text": "I quit Acme and joined Google.",
            },
            {
                "action": "assert_active",
                "expected": {"subject": "user", "predicate": "employer", "value": "Google"},
            },
            {
                "action": "assert_not_active",
                "expected": {"subject": "user", "predicate": "employer", "value": "Acme Corp"},
            },
            {
                "action": "assert_superseded_exists",
                "expected": {"subject": "user", "predicate": "employer", "value": "Acme Corp"},
            },
            {
                "action": "assert_retrieval",
                "query": "Where does the user work now?",
                "expected_values": ["Google"],
                "unexpected_values": ["Acme Corp"],
            },
        ],
    },
    # ─── Scenario 3: Duplicate detection ─────────────────────────────────
    {
        "name": "Duplicate Detection",
        "description": "State the same fact twice. Should not create a second memory.",
        "steps": [
            {
                "action": "insert",
                "memory": {
                    "subject": "user.sister",
                    "predicate": "name",
                    "value": "Neha",
                    "memory_type": "relationship",
                    "importance": 0.8,
                    "confidence": 1.0,
                },
                "source_text": "My sister's name is Neha.",
            },
            {
                "action": "insert",
                "memory": {
                    "subject": "user.sister",
                    "predicate": "name",
                    "value": "Neha",
                    "memory_type": "relationship",
                    "importance": 0.8,
                    "confidence": 1.0,
                },
                "source_text": "I told you, my sister is Neha.",
                "expected_status": "duplicate",
            },
            {
                "action": "assert_count",
                "status": "active",
                "expected_count": 1,
            },
        ],
    },
    # ─── Scenario 4: Long-range recall ───────────────────────────────────
    {
        "name": "Long-Range Recall (40+ turns simulated)",
        "description": "Insert a fact, add many unrelated facts, then try to retrieve the original.",
        "steps": [
            {
                "action": "insert",
                "memory": {
                    "subject": "user",
                    "predicate": "pet_name",
                    "value": "Mochi",
                    "memory_type": "relationship",
                    "importance": 0.7,
                    "confidence": 1.0,
                },
                "source_text": "My dog's name is Mochi.",
            },
            # Simulate 40 unrelated turns by inserting filler facts
            *[
                {
                    "action": "insert",
                    "memory": {
                        "subject": "user",
                        "predicate": f"filler_fact_{i}",
                        "value": f"filler_value_{i}",
                        "memory_type": "preference",
                        "importance": 0.3,
                        "confidence": 0.5,
                    },
                    "source_text": f"Filler conversation turn {i}.",
                }
                for i in range(40)
            ],
            {
                "action": "assert_retrieval",
                "query": "What is the name of Mochi the dog?",
                "expected_values": ["Mochi"],
            },
        ],
    },
    # ─── Scenario 5: Multiple contradictions in sequence ─────────────────
    {
        "name": "Sequential Contradictions (3 job changes)",
        "description": "Change the same fact 3 times. Only the latest should be active.",
        "steps": [
            {
                "action": "insert",
                "memory": {
                    "subject": "user",
                    "predicate": "city",
                    "value": "San Francisco",
                    "memory_type": "identity",
                    "importance": 0.8,
                    "confidence": 1.0,
                },
                "source_text": "I live in San Francisco.",
            },
            {
                "action": "insert",
                "memory": {
                    "subject": "user",
                    "predicate": "city",
                    "value": "New York",
                    "memory_type": "identity",
                    "importance": 0.8,
                    "confidence": 1.0,
                },
                "source_text": "I moved to New York.",
            },
            {
                "action": "insert",
                "memory": {
                    "subject": "user",
                    "predicate": "city",
                    "value": "London",
                    "memory_type": "identity",
                    "importance": 0.8,
                    "confidence": 1.0,
                },
                "source_text": "Actually I relocated to London.",
            },
            {
                "action": "assert_active",
                "expected": {"subject": "user", "predicate": "city", "value": "London"},
            },
            {
                "action": "assert_not_active",
                "expected": {"subject": "user", "predicate": "city", "value": "San Francisco"},
            },
            {
                "action": "assert_not_active",
                "expected": {"subject": "user", "predicate": "city", "value": "New York"},
            },
            {
                "action": "assert_count",
                "status": "active",
                "subject": "user",
                "predicate": "city",
                "expected_count": 1,
            },
        ],
    },
    # ─── Scenario 6: Decay of stale plans ────────────────────────────────
    {
        "name": "Memory Decay",
        "description": "Old plans should expire; identity facts should not.",
        "steps": [
            {
                "action": "insert_backdated",
                "memory": {
                    "subject": "user",
                    "predicate": "interview",
                    "value": "Acme next Thursday",
                    "memory_type": "plan",
                    "importance": 0.6,
                    "confidence": 1.0,
                },
                "source_text": "I have an interview at Acme next Thursday.",
                "days_old": 60,
            },
            {
                "action": "insert_backdated",
                "memory": {
                    "subject": "user",
                    "predicate": "name",
                    "value": "Tanmay",
                    "memory_type": "identity",
                    "importance": 1.0,
                    "confidence": 1.0,
                },
                "source_text": "My name is Tanmay.",
                "days_old": 90,
            },
            {
                "action": "decay",
                "max_age_days": 30,
            },
            {
                "action": "assert_not_active",
                "expected": {"subject": "user", "predicate": "interview", "value": "Acme next Thursday"},
            },
            {
                "action": "assert_active",
                "expected": {"subject": "user", "predicate": "name", "value": "Tanmay"},
            },
        ],
    },
    # ─── Scenario 7: Persona consistency check ───────────────────────────
    {
        "name": "Persona Consistency",
        "description": "Verify persona prompt contains canonical traits and invariants.",
        "steps": [
            {
                "action": "assert_persona_contains",
                "expected_strings": [
                    "Robin",
                    "Warm",
                    "quiet cafés",
                    "NEVER CONTRADICT",
                    "canonical persona configuration",
                ],
            },
        ],
    },
]
