# Implementation Tasks

This is the primary tracker for the implementation phase. Check off items as they are completed.

## Core Loop
- [ ] Initialize Python project
- [ ] Add `.env` environment configuration
- [ ] Implement LLM provider adapter (OpenAI/Anthropic)
- [ ] Implement interactive CLI loop (`app.cli`)

## Memory Persistence
- [ ] Create SQLite schema initialization script (`app.init_db`)
- [ ] Add memory repository layer (CRUD operations for SQLite)
- [ ] Verify restart persistence (save basic chat history, reload on restart)

## Memory Extraction
- [ ] Define `Memory` Pydantic extraction schema
- [ ] Implement memory-worthiness classification logic
- [ ] Implement structured extraction via LLM strict outputs
- [ ] Ensure `source_text` provenance is stored with every memory

## Retrieval
- [ ] Implement candidate search (keyword extraction / FTS)
- [ ] Add basic ranking formula (relevance + importance + recency)
- [ ] Add top-K active memory selection and prompt injection
- [ ] Add `/memories` debug output to CLI

## Contradiction Handling
- [ ] Add logic to find existing related memories by `subject` and `predicate`
- [ ] Implement duplicate handling (update `last_accessed_at`)
- [ ] Implement supersession (mark old as `superseded`, link `supersedes_id`)
- [ ] Add historical status fallback
- [ ] Add deterministic tests for contradiction flows

## Persona
- [ ] Define canonical persona in `config/persona.yaml`
- [ ] Add persona loader in `PersonaManager`
- [ ] Inject persona invariants into system prompt
- [ ] Add consistency tests for stable opinions

## Testing
- [ ] Unit tests for memory formatting and schema validation
- [ ] Process restart / persistence integration test
- [ ] Expected recall integration test
- [ ] Contradiction resolution integration test
- [ ] Long-range (50-turn) persona consistency test

## Optional Evaluation (Stretch Goal)
- [ ] Create synthetic conversation scenarios
- [ ] Implement deterministic scoring script based on SQLite state
- [ ] Implement optional LLM-as-judge for tone drift
- [ ] Generate evaluation metrics report

## Submission Preparation
- [ ] Review and clean up `README.md`
- [ ] Fill out `KNOWN_LIMITATIONS.md`
- [ ] Finalize `DEMO_SCRIPT.md`
- [ ] Verify clean setup instructions in new environment
- [ ] Final repository review against architectural constraints
