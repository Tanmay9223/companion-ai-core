# Demo Script

This document outlines a 15-20 minute technical walkthrough for an interview or recorded demonstration. 

*Objective: Optimize for proving the architecture works, not just showing off a polished chatbot.*

---

### Minute 0-2: Introduction & Objective
- **Explain the Problem**: Standard LLMs lose context when the context window fills, and simply passing the entire conversation history is inefficient and doesn't represent actual "learning".
- **Design Objective**: Demonstrate a system that extracts structured facts, resolves contradictions, and injects only relevant memories back into the prompt, mimicking human-like durable memory.
- **Why Conversation History is Insufficient**: Explain that history is literal; memory requires abstraction, classification, and lifecycle management.

### Minute 2-5: Architecture Overview
- **Show Architecture**: Briefly bring up `ARCHITECTURE.md` or a diagram showing the Request Lifecycle.
- **Memory Schema**: Show the SQLite schema. Highlight the `status` and `supersedes_id` fields as the core mechanism for contradiction resolution.
- **Persona Configuration**: Open `config/persona.yaml`. Show the stable traits (e.g., "Prefers quiet cafés") and explain how canonical persona is prioritized over generated chat history to prevent drift.

### Minute 5-9: Demo Persistent Memory
- **Action**: Start the CLI app (`python -m app.cli`).
- **Input**: `User: I'm interviewing at Acme next Thursday.`
- **Action**: Terminate the process (Ctrl+C). Restart the CLI app.
- **Input**: `User: What was the thing I had coming up this week?`
- **Result**: The companion successfully recalls the Acme interview. Explain how SQLite enables this cross-session persistence.

### Minute 9-12: Demo Contradiction Handling
- **Input**: `User: I'm dating Maya.`
- **Action**: Use the `/memories` debug command to show the memory stored as `active`.
- **Input**: `User: Maya and I broke up last week.`
- **Action**: Use `/memories` again (or run the memory inspector script). 
- **Result**: Demonstrate that the old memory status is now `superseded`, a new active memory exists (single/broke up), and it links to the old one. The system resolved the contradiction rather than duplicating facts.

### Minute 12-14: Demo Relevance
- **Action**: Use a script to populate the database with several unrelated memories (favorite color, car, sibling's name).
- **Input**: Ask a targeted question related to just one of those facts.
- **Result**: Turn on debug mode to show the constructed LLM prompt. Prove that *only* the relevant memory was retrieved and injected, avoiding a full memory dump.

### Minute 14-16: Demo Persona Consistency
- **Input**: Ask a question targeting the YAML config: "Do you prefer big parties or quiet cafés?"
- **Result**: The companion answers "quiet cafés". 
- **Explanation**: Note how this anchors the companion's personality, ensuring that even after 50 turns of varying topics, the core character remains completely stable.

### Minute 16-18: Tests and Evaluation
- **Action**: Run `pytest tests/`.
- **Result**: Show that the contradiction and duplicate detection logic are deterministically tested without needing an LLM-in-the-loop.
- **Action (If implemented)**: Run the evaluation harness to show synthetic multi-turn results.

### Minute 18-20: Limitations & Retrospective
- **Discuss Known Limitations**: Point out `KNOWN_LIMITATIONS.md`. Acknowledge that LLM extraction isn't perfect, entity resolution is hard, and semantic retrieval needs tuning.
- **Future Improvements**: Discuss what you would do with another week (e.g., adding local embeddings for better semantic search, graph database for complex relationships).
- **Intentionally Omitted**: Remind the reviewer that UI, Auth, and production infrastructure were intentionally skipped to focus 100% on the core memory loop.
