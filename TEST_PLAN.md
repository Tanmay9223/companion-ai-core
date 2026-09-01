# Test Plan

This document outlines the testing strategy for the Companion-AI core loop, prioritizing deterministic behavior of the memory subsystem.

## Unit Tests

Unit tests should execute entirely locally without calling the external LLM API (using mocks for extraction/generation).

- **Memory Persistence**: Verify that writing a `Memory` object to SQLite and reading it back yields identical data.
- **Memory Schema Validation**: Verify that the Pydantic schema rejects invalid memory types or out-of-bounds importance scores.
- **Normalization**: Verify that entity normalization functions correctly map variations (e.g., "my mom" -> "user.mother").
- **Duplicate Detection**: Provide an identical candidate memory to an existing active memory and assert that the database count does not increase, but `last_accessed_at` is updated.
- **Supersession**: Provide a contradictory candidate memory. Assert that the old memory status becomes `superseded`, the new memory becomes `active`, and `supersedes_id` is linked.
- **Retrieval Ranking**: Mock a database with 10 memories. Pass a specific query and assert that the retrieval function ranks the semantically relevant memory highest.
- **Persona Loading**: Verify that `config/persona.yaml` parses correctly and populates the `PersonaManager` state.
- **Prompt Construction**: Verify that the Context Builder correctly concatenates the persona, retrieved memories, and chat history into the final LLM prompt string.

## Integration Tests

Integration tests run multi-turn scenarios to test the orchestrator. These may use a mocked LLM (scripted responses) or a fast, cheap LLM model for real evaluation.

### Persistent Recall
**Session 1:**
- User: "I have a golden retriever named Bruno."
- *Action*: Terminate process/session.
**Session 2:**
- User: "What was my dog's name again?"
- *Expected*: Memory is retrieved. Response uses "Bruno" correctly.

### Contradiction
**Earlier:**
- User: "I work at Stripe."
**Later:**
- User: "I left Stripe last month."
**Then:**
- User: "Where do I work?"
- *Expected*: System must not confidently say the user currently works at Stripe. Historical Stripe employment may be mentioned contextually (e.g., "You recently left Stripe").

### Preference Recall
**Early:**
- User: "I really dislike crowded places."
**Many turns later:**
- User: "Would a music festival be a good weekend plan for me?"
- *Expected*: The retrieved preference influences the answer naturally (e.g., "Since you dislike crowds, a music festival might be overwhelming...").

### Long-Range Persona Consistency
**Early:**
- User: "Do you prefer big parties or quiet cafés?"
- *Action*: Run 40 dummy conversational turns.
**Later:**
- User: "Big nightclub or tiny café?"
- *Expected*: Core preference (tiny café) remains consistent, overriding any noise introduced in the 40 turns.

### Memory Relevance
**Setup:**
- Insert 10 unrelated memories (favorite color, sister's name, car model, etc.) directly into SQLite.
**Action:**
- User: "What kind of car do I drive?"
- *Expected*: Only the car-related memory enters the constructed prompt context (verifiable via debug output or prompt inspection).

## Failure Classification

When evaluation tests fail, they should be classified into one of the following categories to guide debugging:

- `false_negative_recall`: The system failed to retrieve a relevant active memory it had stored.
- `false_positive_recall`: The system retrieved an entirely irrelevant memory.
- `stale_memory`: The system retrieved and stated a `superseded` or `historical` fact as if it were currently true.
- `contradiction_failure`: The system failed to detect a contradiction during extraction, resulting in two conflicting `active` memories (e.g., works at Acme AND works at Stripe).
- `duplicate_memory`: The system stored the exact same fact multiple times instead of updating access time.
- `persona_fact_drift`: The companion contradicted its own canonical configuration (e.g., saying it loves sunny days when the YAML says rain).
- `persona_tone_drift`: The companion slipped into generic "As an AI language model" speak or corporate assistant tone.
