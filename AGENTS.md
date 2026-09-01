# Agent Instructions

This document provides guidelines for future AI coding agents working within this repository. 

## Project Goal
Build a prototype of a companion-style conversational AI with a robust, persistent memory architecture and consistent persona handling. The primary objective is to maximize the quality of the core memory subsystem within a constrained ~18-hour build window.

## Priority Order
1. Persistence (surviving process restarts)
2. Memory extraction (structured storage)
3. Retrieval (fetching relevant facts)
4. Contradiction resolution (superseding old facts)
5. Persona consistency (anchoring character)
6. Testing (deterministic validation)
7. Evaluation (synthetic scripts)
8. Submission polish

## Architectural Invariants
- **SQLite is the source of truth**: Do not introduce external databases (Postgres, Pinecone) without explicit justification and user approval.
- **Structured Memory**: Memories are stored as structured rows (`subject`, `predicate`, `value`, `status`), not just raw text dumps.
- **Historical Retention**: Old memories are marked as `superseded`, never permanently deleted.
- **Canonical Persona**: Persona config (`config/persona.yaml`) is immutable and loaded separately from user memory.

## Source of Truth Files
- Memory semantics: `MEMORY_DESIGN.md`
- System lifecycle: `ARCHITECTURE.md`
- Persona definition: `config/persona.yaml` and `PERSONA_DESIGN.md`

## Coding Expectations
- Prefer small, inspectable modules over framework-heavy abstractions.
- Preserve provenance (the original `source_text`) for all extracted memories.
- Keep the interface simple (CLI / Terminal script). 

## Testing Requirements
- Every contradiction-related change requires deterministic unit tests.
- Every persistence change requires restart testing.

## Strict Scope Restrictions (Rules)
When working in this repository, you must adhere to the following rules:

1. Do not introduce UI work (Web/Mobile) unless explicitly requested.
2. Do not replace SQLite with external infrastructure without justification.
3. Do not treat full conversation history as long-term memory.
4. Do not store every message as a durable memory; filter for memory-worthiness.
5. Canonical persona configuration has higher priority than generated persona statements.
6. Every contradiction-related change requires tests.
7. Every persistence change requires restart testing.
8. Prefer small, inspectable modules over framework-heavy abstractions.
9. Preserve provenance for extracted memories.
10. Never silently discard superseded facts if historical context could matter.
