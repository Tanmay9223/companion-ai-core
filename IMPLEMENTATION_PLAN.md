# Implementation Plan

This document outlines the prioritized execution plan to build the Companion-AI memory and evaluation loop within an approximately 18-hour constraint.

---

### Phase 1: Skeleton and Persistence
**Goals:**
- CLI loop
- LLM provider abstraction
- SQLite setup
- Session restart verification

**Tasks:**
- Initialize Python project, `.env`, and requirements.
- Create `app.cli` loop for basic read-eval-print.
- Create basic LLM adapter capable of streaming responses.
- Implement SQLite connection and initialization script.
- Verify that standard conversation history is saved and restored across CLI restarts.

**Definition of Done:** User can chat from the terminal, terminate the process, restart it, and see previous context recovered.
**Estimated Effort:** 2-3 hours
**Risks:** Getting bogged down in CLI formatting. Keep it simple.

---

### Phase 2: Memory Extraction
**Goals:**
- Candidate memory extraction
- Structured schema
- Memory-worthiness filtering

**Tasks:**
- Define the `Memory` Pydantic schema based on `ARCHITECTURE.md`.
- Implement `Extractor` class that calls the LLM with a strict prompt/JSON schema to extract facts from user messages.
- Implement filter logic: only store personal durable facts, discard casual chat.
- Write extracted facts to the SQLite `memories` table.

**Definition of Done:** Personal durable facts are stored in SQLite; casual conversational statements are ignored; stored memories can be inspected via script.
**Estimated Effort:** 3-4 hours
**Risks:** LLM returning malformed JSON. *Mitigation: Use structured outputs or strict function calling API.*

---

### Phase 3: Retrieval
**Goals:**
- Relevant memory retrieval
- Top-K context injection
- Avoid full memory dump

**Tasks:**
- Implement a basic retrieval query builder (using keyword extraction or FTS).
- Implement retrieval scoring based on matches, importance, and recency.
- Inject the top 3-5 retrieved active memories into the LLM system prompt.
- Add debug `/memories` command to CLI to show what was retrieved.

**Definition of Done:** Previously mentioned information is successfully recalled and used in generating answers; irrelevant memories are mostly excluded from the prompt.
**Estimated Effort:** 3 hours
**Risks:** Retrieval is too naive and misses semantic matches. *Mitigation: Keep the test cases simple; if time permits in Phase 7, add lightweight embeddings.*

---

### Phase 4: Contradiction Resolution
**Goals:**
- Match new facts against active memories
- Supersede outdated facts
- Preserve historical state

**Tasks:**
- Implement contradiction detection logic in `ContradictionResolver`.
- On new candidate memory extraction, query SQLite for existing active memories by `subject` and `predicate`.
- Use LLM to classify if the new fact duplicates, enriches, or contradicts the old fact.
- Update SQLite: mark old as `superseded`, insert new, link via `supersedes_id`.

**Definition of Done:** Relationship status updates or job status updates work correctly without duplicating facts. The old fact is not presented as current truth.
**Estimated Effort:** 3-4 hours
**Risks:** Tricky edge cases where facts partially overlap. *Mitigation: Rely heavily on standardizing the `predicate` field during extraction.*

---

### Phase 5: Persona Consistency
**Goals:**
- Canonical persona file
- Persona instructions
- Companion fact protection
- Long-conversation stability

**Tasks:**
- Create `config/persona.yaml`.
- Implement `PersonaManager` to load the config.
- Update the system prompt to explicitly prioritize the canonical persona over conversational context.
- Define 3-5 stable opinions and traits in the YAML.

**Definition of Done:** Repeated persona questions across a long session produce semantically consistent answers; the system does not collapse into a generic "AI assistant" tone.
**Estimated Effort:** 1-2 hours
**Risks:** Prompt drift. *Mitigation: Ensure the persona block is placed at the very end or highly emphasized part of the system prompt.*

---

### Phase 6: Testing
**Goals:**
- Deterministic unit and integration tests.

**Tasks:**
- Write unit test for memory insertion and schema validation.
- Write test for duplicate detection and supersession logic.
- Write integration test for restart persistence.
- Write test for persona configuration loading.

**Definition of Done:** `pytest` passes reliably on all critical memory logic paths.
**Estimated Effort:** 2 hours
**What to skip if running out of time:** Deep integration tests simulating 50 turns.

---

### Phase 7: Evaluation Stretch Goal
**Goals:**
- Implement only after Phases 1-6 are working.

**Tasks:**
- Create a synthetic evaluation script (`eval/run_evals.py`).
- Create deterministic assertions on the SQLite database state after passing a script of messages.
- Implement an optional LLM-as-judge to evaluate tone drift.

**Definition of Done:** Synthetic scenarios run automatically and output a metrics report.
**Estimated Effort:** 2-3 hours
**What to skip if running out of time:** Entire phase. Evaluation is optional and secondary to a working core loop.

---

### Phase 8: Submission Preparation
**Goals:**
- Polish and document.

**Tasks:**
- README cleanup (add exact run commands).
- Verify architecture documentation matches the final implementation.
- Fill out `KNOWN_LIMITATIONS.md`.
- Prepare `DEMO_SCRIPT.md` with explicit copy-pasteable inputs.
- Final manual run-through of the demo script.

**Definition of Done:** Repository is ready for interviewer review.
**Estimated Effort:** 1-2 hours
