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
