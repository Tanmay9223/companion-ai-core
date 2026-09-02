# Companion-AI Core Loop: Memory & Evaluation

A prototype companion-style conversational AI with persistent memory, contradiction handling, and consistent persona — built for the Tech Generalist take-home assignment.

---

## Prerequisites

Install **Docker** on your machine or VM:
- **Mac**: https://docs.docker.com/desktop/install/mac-install/
- **Windows**: https://docs.docker.com/desktop/install/windows-install/
- **Linux (Ubuntu/Debian)**:
  ```bash
  sudo apt-get update && sudo apt-get install -y docker.io
  sudo systemctl start docker
  sudo usermod -aG docker $USER
  # Log out and log back in, then verify:
  docker --version
  ```

That's it. No Python, no pip, no virtual environments needed.

---

## Quick Start (3 steps)

### Step 1: Clone the repo

```bash
git clone https://github.com/Tanmay9223/companion-ai-core.git
cd companion-ai-core
```

### Step 2: Add your API key

```bash
cp .env.example .env
```

Open `.env` in any editor and replace `your_api_key_here` with your real OpenAI API key:

```
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
```

### Step 3: Run

```bash
./run.sh
```

This builds the Docker image, installs all dependencies inside the container, and starts the interactive chat. Your memory database is stored in `./data/` so it persists across runs.

> **Windows users**: If `./run.sh` doesn't work, run the two commands manually:
> ```bash
> docker build -t companion-ai .
> docker run -it --rm --env-file .env -v "%cd%/data:/app/data" -e DB_PATH=/app/data/memory.sqlite companion-ai
> ```

---

## Run Tests

```bash
./run_tests.sh
```

Or manually:

```bash
docker build -t companion-ai .
docker run --rm companion-ai pytest tests/ -v
```

No API key needed for tests — they use deterministic SQLite fixtures.

---

## Run Evaluation Harness

```bash
./run_evals.sh
```

Or manually:

```bash
docker build -t companion-ai .
docker run --rm companion-ai python -m eval.run_evals
```

No API key needed — the eval harness drives the memory engine directly with synthetic data.

**Latest results: 72/72 assertions passed, 7/7 scenarios passed (100% pass rate)**

The harness covers 7 scenarios:

| # | Scenario | What it tests |
|---|---|---|
| 1 | Basic Fact Insertion and Recall | Store a fact, verify retrieval |
| 2 | Contradiction Supersession | Old fact → superseded, new fact → active |
| 3 | Duplicate Detection | Same fact twice → no duplicate created |
| 4 | Long-Range Recall (40+ turns) | Insert 40 filler facts, still retrieve original |
| 5 | Sequential Contradictions (3 changes) | Only latest value is active |
| 6 | Memory Decay | Old plans expire, identity facts don't |
| 7 | Persona Consistency | YAML traits present in system prompt |

**Weaknesses identified by the harness:**
1. Retrieval is keyword-based — semantically similar but lexically different queries will miss
2. Entity normalization depends on LLM consistency
3. Persona consistency is strongly prompted but not mathematically guaranteed
4. Decay is time-based only — no semantic decay for emotional states

---

## CLI Commands

Once inside the chat loop:

| Command | What it does |
|---|---|
| `/memories` | Show all active memories |
| `/history` | Show all memories including superseded and expired |
| `/debug` | Toggle debug mode (shows what context was injected) |
| `/exit` | Quit |

---

## Demo Flow

1. Start: `./run.sh`
2. Say: *"I work at Acme as a software engineer."*
3. Say: *"My sister Neha is visiting next weekend."*
4. Quit: `/exit`
5. Start again: `./run.sh`
6. Ask: *"What do you remember about me?"* → Should recall Acme and Neha
7. Say: *"I quit Acme and joined Google."*
8. Type `/history` → Old "Acme" memory shows as superseded, "Google" is active
9. Ask: *"Do you prefer big parties or quiet cafés?"* → Robin should answer with its canonical persona (prefers quiet cafés)

---

## Inspect the Database (outside the chat)

```bash
docker build -t companion-ai .
docker run --rm -v "$(pwd)/data:/app/data" -e DB_PATH=/app/data/memory.sqlite companion-ai python -m app.inspect_memory
```

---

## Architecture

```
User Input
   ↓
Retrieve Relevant Memories (keyword + importance + recency scoring)
   ↓
Build Prompt = Persona (YAML) + Retrieved Memories + Recent Conversation History
   ↓
LLM generates response
   ↓
Extract structured facts from user message (subject, predicate, value)
   ↓
Resolve: New? Duplicate? Contradiction? → Insert / Skip / Supersede
   ↓
SQLite (persists across restarts)
```

**Key design choices**:

| Decision | Why |
|---|---|
| SQLite, not Postgres/Vector DB | Zero infra, transactional, inspectable, perfect for structured contradiction matching |
| Structured facts `(subject, predicate, value)`, not embeddings | Deterministic contradiction detection — if `(user, employer)` already exists, a new value supersedes it |
| Persona loaded from immutable YAML | Prevents identity drift — canonical traits can't be overwritten by conversation |
| Keyword retrieval, not vector search | Achievable in the time constraint; exact entity match + importance weighting |

See [`DECISIONS.md`](DECISIONS.md) for full architecture decision records.

---

## What Was Tried and Abandoned

- **Vector embeddings**: Considered `sentence-transformers` for cosine-similarity retrieval. Dropped — structured `(subject, predicate)` matching was more critical for contradiction detection, and keyword scoring was sufficient for the demo.
- **LLM-in-the-loop contradiction resolution**: Passing old+new memory to the LLM to classify the relationship. Dropped — too slow and non-deterministic. Exact-match is faster and testable.
- **Graph-based entity resolution**: Modeling entities as a graph. Dropped — dot-notation (`user.sister.Neha`) captures hierarchy in a simpler flat schema.
- **Streaming responses**: `stream=True` for better UX. Dropped — focus is on memory architecture, not UX polish.

---

## Known Limitations

- Entity normalization depends on LLM consistency (mitigated with few-shot examples in the extraction prompt)
- Keyword retrieval may miss semantically similar but lexically different queries
- Persona consistency is strongly prompted but not mathematically guaranteed
- See [`KNOWN_LIMITATIONS.md`](KNOWN_LIMITATIONS.md) for the full list (10 items)

---

## Out of Scope (per assignment §4)

- UI/UX polish
- Authentication, billing, multi-user
- Voice, image, video
- Production infrastructure

---

## Project Structure

```
├── app/
│   ├── __main__.py            # Entrypoint (python -m app)
│   ├── cli.py                 # Interactive chat loop
│   ├── llm_adapter.py         # OpenAI API integration
│   ├── extractor.py           # LLM-powered memory extraction
│   ├── memory_store.py        # SQLite CRUD + contradiction resolution + decay
│   ├── retriever.py           # Relevant memory retrieval with scoring
│   ├── conversation_history.py # Cross-session conversation persistence
│   ├── persona_manager.py     # YAML persona → system prompt
│   ├── schema.py              # Pydantic models for structured extraction
│   ├── init_db.py             # SQLite schema initialization
│   └── inspect_memory.py      # Standalone DB inspector
├── config/
│   └── persona.yaml           # Robin's canonical personality
├── eval/
│   ├── scenarios.py           # 7 synthetic test scenarios
│   └── run_evals.py           # Evaluation harness (pass/fail + numbers)
├── tests/                     # 15 deterministic unit tests
├── Dockerfile                 # Containerized build
├── run.sh                     # One-command launcher
├── run_tests.sh               # One-command test runner
├── run_evals.sh               # One-command eval harness runner
├── requirements.txt
├── .env.example
├── ARCHITECTURE.md
├── DECISIONS.md
├── KNOWN_LIMITATIONS.md
└── MEMORY_DESIGN.md
```

