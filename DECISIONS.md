# Architecture Decision Records (ADRs)

This document tracks the major engineering decisions made during the design of the Companion-AI core loop.

## ADR-001 Persistent Store

**Decision:**
Use SQLite as the primary persistent data store.

**Reasoning:**
- **Zero Infrastructure:** Requires no external database servers or Docker containers, perfect for a prototype and local assignment.
- **Durable & Transactional:** Safely handles process exits and restarts.
- **Inspectable:** Easy to query directly via CLI or GUI tools to prove state changes during a demo.
- **Relational:** Supports the structured nature of our memory model (status tracking, foreign keys for supersession).

**Alternatives Considered:**
- *JSON Files*: Prone to corruption on concurrent writes; difficult to query efficiently.
- *PostgreSQL*: Overkill for a local prototype; introduces setup friction.
- *Vector Database (Pinecone/Chroma)*: Good for semantic search, but lacks robust relational capabilities needed for strict contradiction handling.

## ADR-002 Structured Memory

**Decision:**
Use structured semantic facts (Subject, Predicate, Value) as the primary representation of memory, rather than relying solely on raw text embeddings.

**Reasoning:**
- Contradiction detection is significantly easier and more deterministic when facts are structured. If we know the subject is `user.employer`, it is easy to detect when a new candidate memory about `user.employer` arrives.
- With raw text chunks in a vector database, detecting that "I quit Acme" supersedes "I work at Acme" requires complex LLM orchestration that is error-prone.
- Structured data allows for simple metadata filtering (e.g., `WHERE status = 'active'`).

## ADR-003 Retrieval Strategy

**Decision:**
Use a hybrid retrieval approach based on SQLite keyword/FTS matching, importance weighting, and recency, falling back to local embeddings only if time permits.

**Reasoning:**
- A pure semantic vector search might return highly similar but completely irrelevant facts based on phrasing. 
- Hybrid retrieval allows us to quickly fetch exact entity matches (e.g., "Maya") from the structured database.
- It is achievable within the 18-hour constraint without setting up complex embedding pipelines.

## ADR-004 Persona Isolation

**Decision:**
Keep canonical persona configuration completely separate from generated conversational memory.

**Reasoning:**
- Generative models are prone to hallucination and conversational drift. If persona facts are stored in the same mutable memory pool as user facts, the companion might overwrite its own personality based on an accidental statement.
- Loading an immutable YAML file on every turn anchors the model strictly, satisfying the "Persona Consistency" requirement robustly.

## ADR-005 Evaluation Strategy

**Decision:**
Prioritize deterministic unit/integration tests over LLM-as-judge evaluation.

**Reasoning:**
- LLM-as-judge is subjective, non-deterministic, and expensive. It is hard to prove a system works based on an LLM score alone.
- Because we use structured memory (ADR-002), we can write standard `pytest` assertions to check if the database state correctly shifted from `active` to `superseded` after a contradiction. This provides mathematical proof that the core loop logic works.
- LLM evaluation is treated as an optional stretch goal.
