# Memory Design

This document details the memory subsystem, defining what is stored, how it is categorized, and how the system resolves conflicting information over time.

## What Qualifies as Memory?
Memory consists of durable, personal facts about the user, their relationships, preferences, goals, and important life events. To qualify, a statement must have long-term relevance beyond the current conversation. 

## What Does Not Qualify as Memory?
- Casual conversational filler ("That sounds interesting").
- Temporary or immediate state ("I'm drinking water right now", "I have a headache today"), unless it is identified as a recurring pattern.
- The literal conversation history (the transcript). Memory is an abstraction *extracted* from the transcript.

## How is Memory Represented?
Memory is represented as structured, semantic triples (or multi-part records) stored in an SQLite database. 
Key fields: `subject`, `predicate`, `value`, `memory_type`, `importance`, `status`.

## Memory Categories
Extracted memories should be classified into one of the following categories:
- `identity`: Core facts about the user (name, age, traits).
- `relationship`: Facts about people in the user's life (family, friends, partners).
- `employment`: Jobs, career goals, work state.
- `preference`: Likes, dislikes, favored environments.
- `plan`: Upcoming events, scheduled activities.
- `goal`: Long-term ambitions.
- `event`: Past occurrences.
- `emotional_context`: Significant emotional states or recurring concerns.
- `recurring_topic`: Subjects the user frequently brings up.

## Example of Extraction
**Input:**
"My sister Neha is visiting me next weekend."

**Potential extracted memory:**
```json
{
  "subject": "user.sister.Neha",
  "predicate": "visiting_user",
  "value": "next weekend",
  "memory_type": "plan",
  "importance": 0.7,
  "confidence": 0.9
}
```
*Note: We favor structured data over free-form summaries to allow deterministic matching and contradiction handling.*

## How is Importance Assigned?
During extraction, the LLM assigns an `importance` score (0.0 to 1.0). 
- 0.9+: Core identity, major life events (marriage, career change).
- 0.5-0.8: Preferences, plans, relationships.
- < 0.5: Minor preferences, low-stakes events.

## How are Entities Normalized?
The extraction prompt instructs the LLM to use standardized namespaces. The user is always `user`. Relationships are nested (e.g., `user.relationship.partner`). This normalization is critical so that "my girlfriend" and "Maya" map to the same conceptual entity if previously linked.

## Duplicate Detection
Before a candidate memory is inserted, the system queries the active memories for exact matches on `subject`, `predicate`, and `value`. If a match is found, the system simply updates the `last_accessed_at` timestamp of the existing memory and discards the candidate.

## Contradiction Detection & Superseding Facts
When a new memory has the same `subject` and `predicate` but a different `value`, a contradiction occurs. 

**Example Sequence:**

*Turn A:*
"I've been dating Maya for two years."
```text
subject: user.relationship.partner
predicate: identity
value: Maya
status: active
```

*Turn B:*
"Maya and I broke up last week."

*Resulting State:*
```text
old memory:
id: mem_1
subject: user.relationship.partner
predicate: identity
value: Maya
status: superseded

new memory:
id: mem_2
subject: user.relationship.status
predicate: identity
value: single
status: active

new memory 3:
id: mem_3
subject: user.relationship.historical_partner
predicate: identity
value: Maya
status: active
supersedes_id: mem_1
```

## How are Historical Memories Retained?
Superseded memories are never deleted. Their `status` is changed from `active` to `superseded`. They remain in the database for provenance and can be retrieved if a query explicitly asks for historical context (e.g., "Where did I used to work?"). By default, the retrieval layer only fetches `active` memories.

## How does Retrieval Work?
Retrieval is a hybrid ranking function. Given a user query, the system extracts keywords and searches the SQLite store. Results are ranked by:
1. Keyword match score
2. `importance` weight
3. Recency (`last_accessed_at`)

Only the top 3-5 `active` memories are injected into the prompt.

## Decay
In this implementation, decay means that memories with low `importance` that have not been accessed recently (old `last_accessed_at`) receive a lower retrieval score. They are not deleted. Plans that have passed their `valid_to` date (e.g., "next weekend") may automatically have their status downgraded to `historical` via a background cleanup or during retrieval evaluation.

## Low Confidence & Hallucination Avoidance
If the extraction LLM is unsure (confidence < 0.5), the candidate memory is discarded. 
To avoid hallucinated memories, the extraction prompt is strictly constrained to only extract facts explicitly stated by the user in the current turn, utilizing the `source_text` field to maintain a strict chain of provenance.
