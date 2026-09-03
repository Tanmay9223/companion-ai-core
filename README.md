# Companion-AI Core Loop: Memory & Evaluation

A working prototype of a companion-style conversational AI with persistent memory, contradiction handling, and consistent persona.

## How to Run

**Prerequisite:** [Install Docker](https://docs.docker.com/get-docker/) on your machine.

```bash
# 1. Clone
git clone https://github.com/Tanmay9223/companion-ai-core.git
cd companion-ai-core

# 2. Add your API key (supports OpenAI or Google Gemini)
cp .env.example .env
# Edit .env → set LLM_PROVIDER and add your key:
#   For Gemini (free): LLM_PROVIDER=gemini + GOOGLE_API_KEY from https://aistudio.google.com/
#   For OpenAI:        LLM_PROVIDER=openai + OPENAI_API_KEY

# 3. Start the companion
./run.sh

# 4. Run tests (no API key needed)
./run_tests.sh

# 5. Run evaluation harness (no API key needed)
./run_evals.sh
```

## Debugging & Hallucination Inspection

If you want to see exactly how the AI is reasoning, extracting, and recalling facts (or check if it's hallucinating), there are two tools built in:

1. **`companion.log` File**: All background operations (database retrievals, the exact System Prompt constructed, the LLM's raw response, and the structured extraction JSON) are automatically logged to `companion.log` in real-time as you chat.
2. **`/debug` Command**: While chatting in the terminal, type `/debug` to toggle live debugging. This prints the exact injected context and memory extractions directly into your console for every turn.


## Architecture Decisions

```
User Input → Retrieve Relevant Memories → Build Prompt (Persona + Memories + History) → LLM → Response
                                                                                        ↓
                                                                          Extract Facts → Resolve Contradictions → SQLite
```

| Decision | Why |
|---|---|
| **SQLite** over Postgres/Vector DB | Zero infrastructure, transactional, inspectable. Perfect for structured contradiction handling in a prototype. |
| **Structured facts** `(subject, predicate, value)` over embeddings | Enables deterministic contradiction detection — if `(user, employer)` already exists, a new value supersedes it automatically. |
| **Persona from immutable YAML** | Prevents identity drift. Canonical traits can't be overwritten by conversation — they're loaded fresh every turn from `config/persona.yaml`. |
| **Keyword + importance retrieval** over vector search | Achievable within the time constraint. Exact entity matching + importance weighting + recency decay. |
| **LLM-powered structured extraction** (Pydantic) | Guarantees output schema. The LLM returns typed `(subject, predicate, value, importance, confidence)` — not free-text. |

## What Was Tried and Abandoned

- **Vector embeddings for retrieval** — Considered `sentence-transformers` for cosine similarity. Dropped because structured `(subject, predicate)` matching was more critical for contradiction detection, and keyword scoring was sufficient for the demo scenarios.
- **LLM-in-the-loop contradiction resolution** — Considered passing old + new memory to the LLM to classify the relationship. Dropped because it added latency and non-determinism to every write. Exact `(subject, predicate)` matching is faster and testable.
- **Graph-based entity resolution** — Explored modeling entities as a graph. Dropped — dot-notation (`user.sister.Neha`) captures hierarchy in a simpler flat schema.
- **Streaming responses** — Tried `stream=True` for better perceived latency. Dropped to keep the core loop simple and debuggable.

## Known Limitations

1. **Entity normalization** depends on LLM consistency — mitigated with few-shot examples in the extraction prompt, but `"my mom"` vs `"my mother"` may still produce different subjects.
2. **Keyword retrieval** may miss semantically similar but lexically different queries (e.g., `"automobile"` vs `"car"`).
3. **Persona consistency** is strongly prompted but not mathematically guaranteed — the LLM could still slip under adversarial pressure.
4. **Decay is time-based only** — no semantic decay for emotional states (e.g., `"user is stressed about finals"` persists indefinitely if type ≠ plan/event).
5. **No embedding-based reranking** — a cross-encoder reranker on the top retrieval candidates would improve recall.

See [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) for the full list (10 items).

## Evaluation Harness

```bash
./run_evals.sh
```

**Results: 72/72 assertions passed, 7/7 scenarios passed (100% pass rate)**

| # | Scenario | What It Tests |
|---|---|---|
| 1 | Basic Fact Insertion & Recall | Store a fact, verify retrieval |
| 2 | Contradiction Supersession | Old fact → superseded, new fact → active |
| 3 | Duplicate Detection | Same fact twice → no duplicate created |
| 4 | Long-Range Recall (40+ turns) | Insert 40 filler facts, still retrieve original |
| 5 | Sequential Contradictions | 3 job changes → only latest is active |
| 6 | Memory Decay | Old plans expire, identity facts don't |
| 7 | Persona Consistency | Canonical traits present in system prompt |

**Dimension scores:**

| Dimension | Score |
|---|---|
| Memory Recall Accuracy | 100% |
| Contradiction Handling | 100% |
| Duplicate Prevention | 100% |
| Decay Accuracy | 100% |
| Persona Consistency | 100% |

**Failure classes defined:**
`memory_miss` · `memory_hallucination` · `contradiction_leak` · `duplicate_stored` · `decay_failure` · `persona_drift` · `supersession_failure`

**0 failure classes triggered** in this run.

**Weaknesses:**
1. Retrieval is keyword-based — semantically similar but lexically different queries will miss
2. Entity normalization depends on LLM consistency
3. Persona consistency is prompted, not guaranteed
4. Decay is time-based only — no semantic decay for emotional states
