"""Evaluation harness for Companion-AI memory system.

Runs synthetic scenarios against the core memory engine (MemoryStore,
MemoryRetriever, PersonaManager) and produces pass/fail results with
numbers and example failures.

Usage:
    python -m eval.run_evals
    # or inside Docker:
    docker run --rm companion-ai python -m eval.run_evals
"""

import os
import sys
import uuid
import sqlite3
import datetime
import json

# Ensure imports work
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.memory_store import MemoryStore
from app.retriever import MemoryRetriever
from app.persona_manager import PersonaManager
from app.schema import ExtractedMemory
from eval.scenarios import SCENARIOS

EVAL_DB = "eval_memory.sqlite"


def setup_db():
    """Create a fresh SQLite database for evaluation."""
    if os.path.exists(EVAL_DB):
        os.remove(EVAL_DB)
    conn = sqlite3.connect(EVAL_DB)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS memories (
        id TEXT PRIMARY KEY,
        namespace TEXT NOT NULL,
        subject TEXT NOT NULL,
        predicate TEXT NOT NULL,
        value TEXT NOT NULL,
        memory_type TEXT NOT NULL,
        source_text TEXT,
        importance REAL DEFAULT 0.5,
        created_at DATETIME,
        updated_at DATETIME,
        last_accessed_at DATETIME,
        status TEXT DEFAULT 'active',
        supersedes_id TEXT,
        metadata TEXT
    );
    """)
    conn.commit()
    conn.close()


def insert_backdated(db_path, memory_dict, source_text, days_old):
    """Insert a memory with a backdated created_at timestamp."""
    old_date = (datetime.datetime.utcnow() - datetime.timedelta(days=days_old)).isoformat()
    mem_id = str(uuid.uuid4())
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO memories (
            id, namespace, subject, predicate, value, memory_type,
            source_text, importance, created_at, updated_at, last_accessed_at, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        mem_id,
        "user" if memory_dict["subject"].startswith("user") else "companion",
        memory_dict["subject"], memory_dict["predicate"], memory_dict["value"],
        memory_dict["memory_type"], source_text, memory_dict["importance"],
        old_date, old_date, old_date, "active",
    ))
    conn.commit()
    conn.close()
    return mem_id


def run_scenario(scenario):
    """Execute a single scenario and return (pass_count, fail_count, failures)."""
    setup_db()
    store = MemoryStore(db_path=EVAL_DB)
    retriever = MemoryRetriever(db_path=EVAL_DB)
    persona = PersonaManager()

    passes = 0
    fails = 0
    failures = []

    for i, step in enumerate(scenario["steps"]):
        action = step["action"]
        step_label = f"  Step {i+1} ({action})"

        try:
            if action == "insert":
                mem = ExtractedMemory(**step["memory"])
                _, status = store.insert_memory(mem, source_text=step.get("source_text", ""))
                if "expected_status" in step:
                    if status == step["expected_status"]:
                        passes += 1
                    else:
                        fails += 1
                        failures.append(f"{step_label}: expected status '{step['expected_status']}', got '{status}'")
                else:
                    passes += 1  # insertion succeeded

            elif action == "insert_backdated":
                insert_backdated(EVAL_DB, step["memory"], step.get("source_text", ""), step["days_old"])
                passes += 1

            elif action == "decay":
                store.decay_stale_memories(max_age_days=step.get("max_age_days", 30))
                passes += 1

            elif action == "assert_active":
                active = store.get_all_active_memories()
                expected = step["expected"]
                found = any(
                    m["subject"] == expected["subject"]
                    and m["predicate"] == expected["predicate"]
                    and m["value"] == expected["value"]
                    for m in active
                )
                if found:
                    passes += 1
                else:
                    fails += 1
                    failures.append(
                        f"{step_label}: expected active memory {expected}, not found. "
                        f"Active: {[{k: m[k] for k in ['subject','predicate','value']} for m in active]}"
                    )

            elif action == "assert_not_active":
                active = store.get_all_active_memories()
                expected = step["expected"]
                found = any(
                    m["subject"] == expected["subject"]
                    and m["predicate"] == expected["predicate"]
                    and m["value"] == expected["value"]
                    for m in active
                )
                if not found:
                    passes += 1
                else:
                    fails += 1
                    failures.append(f"{step_label}: memory {expected} should NOT be active, but it is")

            elif action == "assert_superseded_exists":
                all_mems = store.get_all_memories_with_status()
                expected = step["expected"]
                found = any(
                    m["subject"] == expected["subject"]
                    and m["predicate"] == expected["predicate"]
                    and m["value"] == expected["value"]
                    and m["status"] == "superseded"
                    for m in all_mems
                )
                if found:
                    passes += 1
                else:
                    fails += 1
                    failures.append(f"{step_label}: expected superseded memory {expected}, not found")

            elif action == "assert_count":
                active = store.get_all_active_memories()
                if "subject" in step and "predicate" in step:
                    active = [
                        m for m in active
                        if m["subject"] == step["subject"] and m["predicate"] == step["predicate"]
                    ]
                if step.get("status") == "active":
                    count = len(active)
                else:
                    count = len(store.get_all_memories_with_status())
                if count == step["expected_count"]:
                    passes += 1
                else:
                    fails += 1
                    failures.append(
                        f"{step_label}: expected {step['expected_count']} memories, got {count}"
                    )

            elif action == "assert_retrieval":
                results = retriever.retrieve_relevant_memories(step["query"], top_k=10)
                values = [r["value"] for r in results]

                for ev in step.get("expected_values", []):
                    if ev in values:
                        passes += 1
                    else:
                        fails += 1
                        failures.append(
                            f"{step_label}: expected '{ev}' in retrieval for query "
                            f"'{step['query']}', got {values}"
                        )
                for uv in step.get("unexpected_values", []):
                    if uv not in values:
                        passes += 1
                    else:
                        fails += 1
                        failures.append(
                            f"{step_label}: '{uv}' should NOT appear in retrieval for query "
                            f"'{step['query']}', but it did"
                        )

            elif action == "assert_persona_contains":
                prompt = persona.get_system_prompt_header()
                for expected_str in step["expected_strings"]:
                    if expected_str in prompt:
                        passes += 1
                    else:
                        fails += 1
                        failures.append(
                            f"{step_label}: expected '{expected_str}' in persona prompt, not found"
                        )

            else:
                fails += 1
                failures.append(f"{step_label}: unknown action '{action}'")

        except Exception as e:
            fails += 1
            failures.append(f"{step_label}: EXCEPTION: {e}")

    # Cleanup
    if os.path.exists(EVAL_DB):
        os.remove(EVAL_DB)

    return passes, fails, failures


def main():
    print("=" * 70)
    print("  COMPANION-AI EVALUATION HARNESS")
    print("  Synthetic scenario-based testing of the core memory engine")
    print("=" * 70)
    print()

    total_passes = 0
    total_fails = 0
    all_failures = []
    scenario_results = []

    for scenario in SCENARIOS:
        passes, fails, failures = run_scenario(scenario)
        total_passes += passes
        total_fails += fails
        all_failures.extend(failures)

        status = "✅ PASS" if fails == 0 else "❌ FAIL"
        scenario_results.append({
            "name": scenario["name"],
            "passes": passes,
            "fails": fails,
            "status": status,
        })
        print(f"  {status}  {scenario['name']}")
        print(f"         {scenario['description']}")
        print(f"         Assertions: {passes} passed, {fails} failed")
        if failures:
            for f in failures:
                print(f"         ⚠  {f}")
        print()

    # ─── Summary ─────────────────────────────────────────────────────────
    total = total_passes + total_fails
    pass_rate = (total_passes / total * 100) if total > 0 else 0

    print("=" * 70)
    print("  RESULTS SUMMARY")
    print("=" * 70)
    print(f"  Scenarios:   {len(SCENARIOS)}")
    print(f"  Assertions:  {total} total")
    print(f"  Passed:      {total_passes}")
    print(f"  Failed:      {total_fails}")
    print(f"  Pass Rate:   {pass_rate:.1f}%")
    print()

    if all_failures:
        print("  EXAMPLE FAILURES:")
        for f in all_failures[:5]:
            print(f"    • {f}")
        print()

    # ─── Weaknesses analysis ─────────────────────────────────────────────
    print("  WEAKNESSES (author assessment):")
    print("    1. Retrieval is keyword-based — semantically similar but lexically")
    print("       different queries (e.g. 'automobile' vs 'car') will miss.")
    print("    2. Entity normalization depends on LLM consistency — 'my mom' vs")
    print("       'my mother' may produce different subjects without few-shot examples.")
    print("    3. Persona consistency is strongly prompted but not mathematically")
    print("       guaranteed — the LLM could still slip under adversarial pressure.")
    print("    4. Decay is time-based only — no semantic decay for emotional states")
    print("       (e.g. 'user is stressed about finals' stays forever if type != plan/event).")
    print()

    scenarios_passed = sum(1 for s in scenario_results if s["fails"] == 0)
    print(f"  {scenarios_passed}/{len(SCENARIOS)} scenarios fully passed.")
    print("=" * 70)

    return 0 if total_fails == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
