# Known Limitations

This document explicitly outlines the weaknesses in the current prototype architecture and proposes potential future improvements. Openly documenting these limitations demonstrates engineering judgment and pragmatic trade-offs made to meet the 18-hour constraint.

## 1. LLM Extraction Reliability
**Limitation:** The LLM responsible for extracting candidate memories from user input can occasionally hallucinate facts, misinterpret nuance, or produce malformed JSON structures that violate the Pydantic schema.
**Future Improvement:** Implement a robust retry mechanism with error-correction prompting. Move to a fine-tuned, smaller model specifically trained on extraction tasks to improve latency and structured output reliability.

## 2. Naive Contradiction Detection
**Limitation:** Relying solely on `subject` and `predicate` matching for contradiction detection works well for simple states (e.g., `user.employer = Acme`) but fails on complex or nuanced changes that don't map cleanly to a rigid schema.
**Future Improvement:** Introduce an LLM-in-the-loop "Resolution" step. When a new memory arrives, fetch *all* loosely related active memories and ask an LLM to output a precise list of mutation operations (create, update, supersede) rather than relying purely on exact string matching.

## 3. Ambiguous Entity Resolution
**Limitation:** If a user says "My sister Neha" in session 1, and then "Neha" in session 2, a naive extraction might create two different subjects (`user.sister.Neha` and `user.Neha`). 
**Future Improvement:** Implement an entity-resolution pre-step. Before saving a memory, compare the candidate entity against a cached list of known entities and prompt the LLM to map ambiguous names to canonical entities.

## 4. Stale Relative Dates
**Limitation:** Extracting a value like "next weekend" becomes semantically incorrect as time passes.
**Future Improvement:** Inject the current system datetime into the extraction prompt and require the LLM to output absolute ISO-8601 timestamps for any date-based memories, storing them in a dedicated `datetime` field in SQLite.

## 5. Semantic Retrieval Tuning
**Limitation:** A purely keyword-based SQLite FTS approach will miss semantic matches (e.g., "automobile" vs "car"). If local embeddings are used, cosine similarity thresholds require manual tuning and are sensitive to phrasing.
**Future Improvement:** Implement a reranking pipeline: use fast vector search to get top 20 candidates, then use a Cross-Encoder model to rerank the top 5 most relevant memories based on the exact conversational context.

## 6. Emotional Context Expiration
**Limitation:** A memory like "User is stressed about finals" has no obvious expiration date. If retrieved 6 months later, it might make the companion seem socially unaware.
**Future Improvement:** Add a `valid_to` or `decay_rate` field to the memory schema. Highly emotional or temporary states should naturally degrade from `active` to `historical` after a configurable time window unless reinforced by the user.

## 7. LLM Generation Overriding Context
**Limitation:** Even if the exact, correct memory is injected into the context window, the generation LLM might still hallucinate or ignore it due to internal model biases.
**Future Improvement:** Use a highly constrained system prompt with "Strict adherence to provided facts" instructions. Utilize models that score highly on needle-in-a-haystack and context-following benchmarks.

## 8. Persona Consistency Not Guaranteed
**Limitation:** While prioritizing the YAML configuration heavily reduces drift, it does not mathematically guarantee that the LLM won't slip into "assistant tone".
**Future Improvement:** Run a fast, small classifier on the output stream. If the classifier detects "As an AI language model..." or similar generic phrasing, halt the stream and retry the generation with a stronger penalty.

## 9. Synthetic Evaluation Dataset
**Limitation:** The evaluation harness relies on scripted, synthetic conversations which may not accurately reflect the messiness of real human chat.
**Future Improvement:** Collect a small dataset of real human interactions (with consent) to serve as the golden dataset for future evaluation runs.

## 10. LLM Judges are Subjective
**Limitation:** Using an LLM to evaluate tone or semantic recall introduces non-determinism and model bias.
**Future Improvement:** Rely primarily on structured SQLite state assertions. Use LLM judges only for aggregate trend analysis, not for strict CI/CD pass/fail gating.
