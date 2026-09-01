# Companion-AI Core Loop: Memory & Evaluation

## Project Purpose
This project is a prototype of a companion-style conversational AI. The goal is to demonstrate a robust, persistent memory architecture and consistent persona handling, showing that the system can truly "remember" facts across sessions, handle contradictions, and maintain character, rather than just relying on a large LLM context window.

## Assignment Scope
This project is built within an approximately 18-hour constraint for a Founding Engineer / Tech Generalist assignment. The core focus is on the memory subsystem (extraction, retrieval, and contradiction handling) and persona consistency.

## Core Capabilities
- **Persistent Memory**: Retains facts across CLI restarts and process exits using a durable data store.
- **Selective Memory Extraction**: Identifies and stores durable facts (e.g., relationships, preferences) while ignoring casual chatter.
- **Smart Retrieval**: Fetches only relevant active memories for context, keeping the prompt focused and efficient.
- **Contradiction Resolution**: Detects when a newly extracted fact supersedes an old one (e.g., changing jobs, relationship status updates) and updates the memory state while preserving historical context.
- **Persona Consistency**: Maintains a canonical character definition that is robust against conversational drift.

## Architecture Summary
The system operates as a CLI application that orchestrates an LLM with a dedicated memory store. 
- **Memory Store**: SQLite is used for persistent, structured memory representation.
- **Request Lifecycle**: The orchestrator receives input, fetches relevant active memories and canonical persona data, builds the LLM context, generates a response, extracts any new facts, resolves contradictions, and updates the memory store.

## Technology Stack
- **Language**: Python 3.11+
- **Database**: SQLite (built-in)
- **Schemas**: Pydantic
- **Testing**: `pytest`
- **Environment**: `python-dotenv`
- **LLM Provider**: (e.g., OpenAI SDK, Anthropic SDK)

## Setup Instructions
1. Clone the repository and navigate to the project root.
2. Create a virtual environment: `python3 -m venv venv`
3. Activate the environment: `source venv/bin/activate` (or `venv\Scripts\activate` on Windows)
4. Install dependencies: `pip install -r requirements.txt` (or similar depending on package manager).
5. Initialize the database schema: `python -m app.init_db`

## Environment Variables
Create a `.env` file in the root directory based on `.env.example`:
```
LLM_API_KEY=your_api_key_here
LLM_PROVIDER=openai  # or anthropic
DB_PATH=./memory.sqlite
```

## How to Run the Chat Loop
Start the interactive terminal application:
```bash
python -m app.cli
```

## How Persistent Memory Works
The system uses SQLite to store facts as structured rows (subject, predicate, value). When you chat, an extraction step identifies facts worth remembering and writes them to SQLite. On restart, the system queries this database, ensuring your previous statements are still accessible.

## How to Inspect the Memory Store
During a chat session, type `/memories` to print a debug view of the current active memories, superseded facts, and their retrieval scores.
Alternatively, use the inspection script:
```bash
python -m app.inspect_memory
```

## How Contradiction Handling Works
When a new candidate memory is extracted (e.g., "I quit Acme"), it is compared against active memories with the same subject/predicate (e.g., "I work at Acme"). If it contradicts, the old memory is marked as `superseded` (retained historically but not used as current truth), and the new memory is marked as `active`.

## How to Run Tests
```bash
pytest tests/
```

## How to Run Evaluation (If Implemented)
Evaluation runs synthetic conversations and deterministic assertions against the memory store:
```bash
python -m eval.run_evals
```

## Known Limitations
- Entity resolution may struggle with highly ambiguous references.
- LLM extraction can occasionally produce unstructured or malformed facts.
- Semantic retrieval requires tuning and may miss subtly related memories.
- See `KNOWN_LIMITATIONS.md` for a comprehensive list.

## What Was Intentionally Left Out
- Web/Mobile UI
- Authentication and Multi-user support
- Cloud infrastructure / distributed vector databases
- Voice and Image modalities

## Suggested Demo Flow
1. Start the app: `python -m app.cli`
2. State a fact: "I'm interviewing at Acme next Thursday."
3. Restart the app. Ask: "What did I have coming up this week?" -> Verify recall.
4. Update a fact: "I didn't get the job at Acme." -> Use `/memories` to see the old fact superseded.
5. Ask a persona question: "Do you prefer big parties or quiet cafes?" -> Verify response aligns with canonical persona.
