# Companion-AI Core Loop: Memory & Evaluation

A prototype companion-style conversational AI with a robust, persistent memory architecture and consistent persona handling.

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 3. Run the companion
python -m app

# 4. Run tests
PYTHONPATH=. pytest tests/ -v
```

## Architecture

The system operates as a CLI application that orchestrates an LLM with a dedicated memory store.

```
User Input → Retrieve Relevant Memories → Build Prompt (Persona + Memories + History) → LLM → Response
                                                                                        ↓
                                                                          Extract Memories → Resolve Contradictions → SQLite
```

- **Memory Store**: SQLite stores structured facts as `(subject, predicate, value)` rows with lifecycle tracking (`active` → `superseded` / `expired`).
- **Retrieval**: Hybrid keyword + importance + recency scoring. Only relevant active memories are injected into the prompt.
- **Contradiction Resolution**: New facts matching the same `(subject, predicate)` as an existing active memory are classified as duplicates or contradictions. Contradictions supersede the old fact while preserving it historically.
- **Memory Decay**: Stale `plan` and `event` memories are automatically expired after 30 days on startup.
- **Persona**: Canonical personality traits, opinions, and style are loaded from `config/persona.yaml` and prioritized over conversational history to prevent identity drift.
- **Conversation History**: Recent turns are persisted to SQLite and restored on restart for cross-session conversational continuity.

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the full component breakdown and request lifecycle.

## CLI Commands

| Command | Description |
|---|---|
| `/memories` | Show all active memories |
| `/history` | Show all memories including superseded and expired |
| `/debug` | Toggle debug mode (shows injected context per turn) |
| `/exit` | Quit the application |

## Inspecting the Database

Outside of a chat session, you can inspect the full memory database:

```bash
python -m app.inspect_memory
```

## Architecture Decisions

| Decision | Reasoning |
|---|---|
| **SQLite** over Postgres/Vector DB | Zero infrastructure, transactional, inspectable, relational — perfect for structured contradiction handling |
| **Structured facts** over raw embeddings | Deterministic contradiction detection via `(subject, predicate)` matching |
| **Hybrid retrieval** over pure vector search | Achievable in constrained time; exact entity matches + importance weighting |
| **Persona isolation** from memory | Prevents identity drift — YAML config is immutable and highest-priority |

See [`DECISIONS.md`](DECISIONS.md) for full ADRs.

## Technology Stack

- **Language**: Python 3.11+
- **Database**: SQLite (built-in)
- **Schemas**: Pydantic (structured LLM outputs)
- **LLM**: OpenAI GPT-4o-mini (configurable)
- **Testing**: pytest
- **Environment**: python-dotenv

## Known Limitations

- Entity resolution may struggle with highly ambiguous references
- LLM extraction can occasionally produce unstructured or malformed facts
- Keyword-based retrieval may miss subtly related memories (embeddings are a future improvement)
- See [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) for a comprehensive list

## What Was Tried and Abandoned

- **Vector embeddings for retrieval**: Initially considered using `sentence-transformers` to compute local embeddings and store them in SQLite for cosine-similarity search. Abandoned because (a) it added a heavy dependency for the MVP, (b) structured `(subject, predicate)` matching was more critical for contradiction detection than semantic similarity, and (c) keyword + importance scoring proved sufficient for the demo scenarios within the 18-hour window.
- **LLM-in-the-loop contradiction resolution**: Considered passing both the old and new memory to the LLM and asking it to classify the relationship (duplicate, enrichment, or contradiction). Abandoned because it added latency and non-determinism to every memory write — the structured `(subject, predicate)` exact-match approach is faster, testable, and deterministic.
- **Graph-based entity resolution**: Explored modeling entities as a graph (e.g., `user → sister → Neha`) to handle complex relationship queries. Deferred as over-engineering for the prototype — the dot-notation subject convention (`user.sister.Neha`) captures the same hierarchy in a simpler flat schema.
- **Streaming responses**: Tried implementing streaming via `stream=True` in the OpenAI API for better UX latency. Abandoned to keep the core loop simple and debuggable — the focus is on memory architecture, not UX polish.

## What Was Intentionally Left Out

- Web/Mobile UI
- Authentication and multi-user support
- Cloud infrastructure / distributed vector databases
- Voice and image modalities
- Production-scale infra, load handling, or latency optimization

## Demo Flow

1. Start the app: `python -m app`
2. State a fact: *"I'm interviewing at Acme next Thursday."*
3. Restart the app (Ctrl+C, then `python -m app`). Ask: *"What did I have coming up?"* → Verify recall.
4. State a contradicting fact: *"I didn't get the job at Acme."* → Use `/memories` and `/history` to see supersession.
5. Ask a persona question: *"Do you prefer big parties or quiet cafés?"* → Verify response aligns with canonical persona.
