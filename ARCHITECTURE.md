# System Architecture

This document describes the core architecture of the Companion-AI system, detailing how memory is processed, stored, and utilized.

## System Components

1. **CLI Chat Interface**: The entry point for user interaction via the terminal. Handles basic `/commands` (like `/memories`) and standard text input.
2. **Conversation Orchestrator**: The central controller that manages the flow of data between the user, the memory subsystem, the persona manager, and the LLM.
3. **Persona Manager**: Loads and enforces the canonical, immutable persona configuration.
4. **Memory Retrieval Layer**: Fetches relevant active memories for a given user query using a hybrid ranking approach.
5. **Prompt / Context Builder**: Assembles the LLM prompt using the user's message, retrieved memories, canonical persona, and recent conversational context.
6. **LLM Provider Adapter**: An abstraction layer for the chosen LLM API (e.g., OpenAI, Anthropic), allowing for easy swapping of models.
7. **Memory Extraction Layer**: Analyzes the user's input (and potentially the LLM's response) to identify candidate facts worth storing.
8. **Contradiction Resolver**: Compares candidate facts against the existing active memory to determine if a fact is new, duplicate, or contradictory.
9. **Memory Store**: The SQLite database serving as the durable source of truth for all memory items.
10. **Evaluation Layer (Optional)**: A separate module for running deterministic and LLM-as-judge evaluations on synthetic conversation scripts.

## Request Lifecycle

The lifecycle of a single user message follows these steps:

1. **Receive User Message**: The CLI captures the input string.
2. **Load Session State**: Retrieve the immediate recent conversation history (e.g., last 5 turns).
3. **Identify Retrieval Query**: Use the user's message (and optionally recent context) to formulate a search query.
4. **Retrieve Relevant Active Memories**: The Retrieval Layer queries the SQLite store for top-K relevant, active facts.
5. **Retrieve Relevant Persona Information**: The Persona Manager provides the canonical identity traits and rules.
6. **Build Constrained Model Context**: The Context Builder formats the system prompt with persona instructions, retrieved facts, and the conversation history.
7. **Generate Companion Response**: The LLM Provider Adapter calls the model and streams/returns the response.
8. **Extract Candidate Memories**: In parallel or sequentially, the Extraction Layer evaluates the user's original message to extract structured `Candidate Memories`.
9. **Compare and Resolve (Contradictions)**: The Contradiction Resolver checks the new candidate memories against existing memories (by subject/predicate). It marks outdated memories as superseded and links the new memory.
10. **Persist Memory Changes**: The Memory Store commits the new/updated records to SQLite.
11. **Persist Minimal Session Metadata**: The conversation turn is saved to the session history.
12. **Return Response**: The generated response is displayed to the user.

*Note: Memory extraction happens **after** (or async to) response generation to minimize latency for the user, as the companion's response relies on past memory, not the memory of the sentence currently being spoken.*

## Memory Architecture

The system uses a hybrid architecture centered around **SQLite** as the persistent source of truth. 

To meet the constraint of a highly reliable core loop without unnecessary infrastructure, we use a structured memory approach. Instead of dumping raw text chunks into a vector database, we extract facts into a structured table (`subject`, `predicate`, `value`).

This enables deterministic contradiction handling (e.g., updating `user.employer` from `Acme` to `None`) which is very difficult to do reliably with raw embeddings alone.

## Memory Schema

Proposed MVP SQLite Schema:

```sql
CREATE TABLE memories (
    id TEXT PRIMARY KEY,
    namespace TEXT NOT NULL,         -- 'user' or 'companion'
    subject TEXT NOT NULL,           -- e.g., 'user.sister.Neha'
    predicate TEXT NOT NULL,         -- e.g., 'visiting_user'
    value TEXT NOT NULL,             -- e.g., 'next weekend'
    memory_type TEXT NOT NULL,       -- 'plan', 'relationship', 'preference', etc.
    source_text TEXT,                -- The original quote for provenance
    importance REAL DEFAULT 0.5,     -- 0.0 to 1.0 weight
    created_at DATETIME,
    updated_at DATETIME,
    last_accessed_at DATETIME,
    status TEXT DEFAULT 'active',    -- 'active', 'superseded', 'historical', 'expired'
    supersedes_id TEXT,              -- Self-referential FK to previous memory
    metadata TEXT                    -- JSON blob for extension
);
```

### Required Fields for MVP:
`id`, `subject`, `predicate`, `value`, `status`, `supersedes_id`, `source_text`.
*(Embeddings are intentionally omitted in the MVP to focus on structured contradiction resolution first, but can be added as an optional field later).*

## Retrieval Strategy

For the MVP, we use a lightweight hybrid ranking strategy that does not require a dedicated vector DB.

**Ranking Formula (Conceptual):**
```text
retrieval_score = 
  keyword_overlap(query, value/subject) * 1.5
  + importance_weight * 0.5
  + recency_weight (based on last_accessed_at)
  - stale_penalty (if memory is old and type is 'plan')
```

**MVP Strategy:** 
Extract keywords from the current turn, perform an SQLite `LIKE` or FTS (Full Text Search) query across active memories, and sort by a combination of relevance and `importance`.

**Optional Improvement:** 
Compute lightweight local embeddings (e.g., via `sentence-transformers`) for the `value` field, store them as JSON or bytes in SQLite, and do local cosine similarity for the top N keyword matches.

## Contradiction Strategy

For every candidate memory extracted from the user's input:

1. **Normalize**: Map the entity and relationship to a standard subject/predicate (e.g., `user` -> `employment` -> `employer`).
2. **Search**: Find any `active` memories with the same `subject` and `predicate`.
3. **Determine Delta**:
   - **Duplicate**: If the `value` is semantically identical, update `last_accessed_at` on the existing memory. Discard candidate.
   - **Enrichment/Separate Event**: If it's a recurring event (e.g., "went to Paris again"), create a new active memory.
   - **Contradiction/Update**: If it fundamentally changes a state (e.g., "quit Acme"), set the old memory's `status` to `superseded`, create the new memory, and set `supersedes_id` pointing to the old one.
4. **Mutate**: Commit the transaction preserving provenance (`source_text`).

## Persona Architecture

Canonical persona traits are stored separately from conversational memory in a version-controlled config file: `config/persona.yaml`.

This file contains immutable traits (identity, voice, core values, boundaries). The Persona Manager loads this file on startup and injects it into the system prompt. 

Because it is loaded from disk and treated as the highest-priority instruction, the agent will not rewrite its canonical identity based on hallucinated statements during a long conversation. If we allow "adaptive" companion memories (e.g., the companion forming a specific opinion about the user), these are stored in the SQLite `memories` table under the `companion` namespace, clearly separated from the canonical YAML configuration.
