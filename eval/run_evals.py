"""Evaluation harness for Companion-AI memory system.

Runs synthetic scenarios against the core memory engine (MemoryStore,
MemoryRetriever, PersonaManager) and produces structured results with
multi-dimensional scores, named failure classes, and example failures.

Uses a hybrid scoring architecture:
  - Rule-based checks for memory state (deterministic)
  - Failure-class taxonomy for rich reporting
  - Aggregated EvalScore per scenario

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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.memory_store import MemoryStore
from app.retriever import MemoryRetriever
from app.persona_manager import PersonaManager
from app.schema import ExtractedMemory
from eval.scenarios import SCENARIOS
from eval.scoring import EvalScore, HarnessReport, FAILURE_CLASSES

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
    """Execute a single scenario and return an EvalScore."""
    setup_db()
    store = MemoryStore(db_path=EVAL_DB)
    retriever = MemoryRetriever(db_path=EVAL_DB)
    persona = PersonaManager()

    score = EvalScore(scenario_name=scenario["name"])

    # Track per-dimension counters
    recall_checks = {"passed": 0, "total": 0}
    contradiction_checks = {"passed": 0, "total": 0}
    duplicate_checks = {"passed": 0, "total": 0}
    decay_checks = {"passed": 0, "total": 0}
    persona_checks = {"passed": 0, "total": 0}

    for i, step in enumerate(scenario["steps"]):
        action = step["action"]
        step_label = f"Step {i+1} ({action})"

        try:
            if action == "insert":
                mem = ExtractedMemory(**step["memory"])
                _, status = store.insert_memory(mem, source_text=step.get("source_text", ""))
                if "expected_status" in step:
                    if status == step["expected_status"]:
                        score.assertions_passed += 1
                        if step["expected_status"] == "duplicate":
                            duplicate_checks["passed"] += 1
                            duplicate_checks["total"] += 1
                    else:
                        score.assertions_failed += 1
                        score.failure_tags.append("duplicate_stored")
                        score.details.append(
                            f"{step_label}: expected status '{step['expected_status']}', got '{status}'"
                        )
                        if step["expected_status"] == "duplicate":
                            duplicate_checks["total"] += 1
                else:
                    score.assertions_passed += 1

            elif action == "insert_backdated":
                insert_backdated(EVAL_DB, step["memory"], step.get("source_text", ""), step["days_old"])
                score.assertions_passed += 1

            elif action == "decay":
                store.decay_stale_memories(max_age_days=step.get("max_age_days", 30))
                score.assertions_passed += 1

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
                    score.assertions_passed += 1
                else:
                    score.assertions_failed += 1
                    # Classify the failure
                    tag = _classify_active_failure(expected, active, store)
                    score.failure_tags.append(tag)
                    score.details.append(
                        f"{step_label}: expected active memory {expected}, not found. "
                        f"[{tag}]"
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
                    score.assertions_passed += 1
                    contradiction_checks["passed"] += 1
                    contradiction_checks["total"] += 1
                else:
                    score.assertions_failed += 1
                    score.failure_tags.append("supersession_failure")
                    score.details.append(
                        f"{step_label}: memory {expected} should NOT be active [supersession_failure]"
                    )
                    contradiction_checks["total"] += 1

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
                    score.assertions_passed += 1
                    contradiction_checks["passed"] += 1
                    contradiction_checks["total"] += 1
                else:
                    score.assertions_failed += 1
                    score.failure_tags.append("supersession_failure")
                    score.details.append(
                        f"{step_label}: expected superseded memory {expected}, not found [supersession_failure]"
                    )
                    contradiction_checks["total"] += 1

            elif action == "assert_count":
                active = store.get_all_active_memories()
                if "subject" in step and "predicate" in step:
                    active = [
                        m for m in active
                        if m["subject"] == step["subject"] and m["predicate"] == step["predicate"]
                    ]
                count = len(active)
                if count == step["expected_count"]:
                    score.assertions_passed += 1
                else:
                    score.assertions_failed += 1
                    tag = "duplicate_stored" if count > step["expected_count"] else "supersession_failure"
                    score.failure_tags.append(tag)
                    score.details.append(
                        f"{step_label}: expected {step['expected_count']} memories, got {count} [{tag}]"
                    )

            elif action == "assert_retrieval":
                results = retriever.retrieve_relevant_memories(step["query"], top_k=10)
                values = [r["value"] for r in results]

                for ev in step.get("expected_values", []):
                    recall_checks["total"] += 1
                    if ev in values:
                        score.assertions_passed += 1
                        recall_checks["passed"] += 1
                    else:
                        score.assertions_failed += 1
                        score.failure_tags.append("memory_miss")
                        score.details.append(
                            f"{step_label}: expected '{ev}' in retrieval for "
                            f"'{step['query']}', got {values} [memory_miss]"
                        )

                for uv in step.get("unexpected_values", []):
                    if uv not in values:
                        score.assertions_passed += 1
                    else:
                        score.assertions_failed += 1
                        score.failure_tags.append("contradiction_leak")
                        score.details.append(
                            f"{step_label}: '{uv}' should NOT appear in retrieval "
                            f"[contradiction_leak]"
                        )

            elif action == "assert_persona_contains":
                prompt = persona.get_system_prompt_header()
                for expected_str in step["expected_strings"]:
                    persona_checks["total"] += 1
                    if expected_str in prompt:
                        score.assertions_passed += 1
                        persona_checks["passed"] += 1
                    else:
                        score.assertions_failed += 1
                        score.failure_tags.append("persona_drift")
                        score.details.append(
                            f"{step_label}: expected '{expected_str}' in persona prompt [persona_drift]"
                        )

            else:
                score.assertions_failed += 1
                score.details.append(f"{step_label}: unknown action '{action}'")

        except Exception as e:
            score.assertions_failed += 1
            score.details.append(f"{step_label}: EXCEPTION: {e}")

    # Compute per-dimension scores
    if recall_checks["total"] > 0:
        score.memory_recall_accuracy = recall_checks["passed"] / recall_checks["total"]
    if contradiction_checks["total"] > 0:
        score.contradiction_handling = contradiction_checks["passed"] / contradiction_checks["total"]
    if duplicate_checks["total"] > 0:
        score.duplicate_prevention = duplicate_checks["passed"] / duplicate_checks["total"]
    if decay_checks["total"] > 0:
        score.decay_accuracy = decay_checks["passed"] / decay_checks["total"]
    if persona_checks["total"] > 0:
        score.persona_consistency = persona_checks["passed"] / persona_checks["total"]

    # Deduplicate failure tags
    score.failure_tags = list(dict.fromkeys(score.failure_tags))

    # Cleanup
    if os.path.exists(EVAL_DB):
        os.remove(EVAL_DB)

    return score


def _classify_active_failure(expected, active_memories, store):
    """Classify why an expected active memory was not found."""
    all_mems = store.get_all_memories_with_status()
    # Check if it exists but was incorrectly superseded
    for m in all_mems:
        if (m["subject"] == expected["subject"]
                and m["predicate"] == expected["predicate"]
                and m["value"] == expected["value"]):
            if m["status"] == "superseded":
                return "supersession_failure"
            if m["status"] == "expired":
                return "decay_failure"
    return "memory_miss"


def main():
    print("=" * 72)
    print("  COMPANION-AI EVALUATION HARNESS")
    print("  Hybrid scoring: deterministic rules + failure-class taxonomy")
    print("=" * 72)
    print()

    report = HarnessReport()

    for scenario in SCENARIOS:
        eval_score = run_scenario(scenario)
        report.scores.append(eval_score)

        status = "✅ PASS" if eval_score.overall_pass else "❌ FAIL"
        print(f"  {status}  {eval_score.scenario_name}")
        print(f"         {scenario['description']}")
        print(f"         Assertions: {eval_score.assertions_passed} passed, {eval_score.assertions_failed} failed")

        # Show per-dimension scores if they were tested
        dims = []
        if eval_score.memory_recall_accuracy < 1.0 or scenario["name"].lower().count("recall") > 0:
            dims.append(f"recall={eval_score.memory_recall_accuracy:.0%}")
        if eval_score.contradiction_handling < 1.0 or "contradiction" in scenario["name"].lower() or "supersess" in scenario["name"].lower():
            dims.append(f"contradiction={eval_score.contradiction_handling:.0%}")
        if eval_score.persona_consistency < 1.0 or "persona" in scenario["name"].lower():
            dims.append(f"persona={eval_score.persona_consistency:.0%}")
        if dims:
            print(f"         Dimensions: {' | '.join(dims)}")

        if eval_score.failure_tags:
            print(f"         Failure classes: {', '.join(eval_score.failure_tags)}")
        if eval_score.details:
            for d in eval_score.details[:3]:
                print(f"         ⚠  {d}")
        print()

    # ─── Summary ─────────────────────────────────────────────────────────
    print("=" * 72)
    print("  RESULTS SUMMARY")
    print("=" * 72)
    print(f"  Scenarios:      {len(report.scores)}")
    print(f"  Scenarios Pass: {report.scenarios_passed}/{len(report.scores)}")
    print(f"  Assertions:     {report.total_assertions} total")
    print(f"  Passed:         {report.total_passed}")
    print(f"  Failed:         {report.total_failed}")
    print(f"  Pass Rate:      {report.overall_pass_rate:.1f}%")
    print()

    # ─── Multi-dimensional scores ────────────────────────────────────────
    print("  DIMENSION SCORES (aggregated across all scenarios):")
    print(f"    Memory Recall Accuracy:    {_avg_dim(report, 'memory_recall_accuracy'):.0%}")
    print(f"    Contradiction Handling:    {_avg_dim(report, 'contradiction_handling'):.0%}")
    print(f"    Duplicate Prevention:      {_avg_dim(report, 'duplicate_prevention'):.0%}")
    print(f"    Decay Accuracy:            {_avg_dim(report, 'decay_accuracy'):.0%}")
    print(f"    Persona Consistency:       {_avg_dim(report, 'persona_consistency'):.0%}")
    print()

    # ─── Failure class breakdown ─────────────────────────────────────────
    tag_counts = report.failure_tag_summary()
    if tag_counts:
        print("  FAILURE CLASS BREAKDOWN:")
        for tag, count in sorted(tag_counts.items(), key=lambda x: -x[1]):
            desc = FAILURE_CLASSES.get(tag, "Unknown failure class")
            print(f"    {tag} ({count}x): {desc}")
        print()
    else:
        print("  FAILURE CLASS BREAKDOWN: None — all checks passed ✅")
        print()

    # ─── Example failures ────────────────────────────────────────────────
    all_details = []
    for s in report.scores:
        all_details.extend(s.details)
    if all_details:
        print("  EXAMPLE FAILURES:")
        for d in all_details[:5]:
            print(f"    • {d}")
        print()

    # ─── Weaknesses analysis ─────────────────────────────────────────────
    print("  KNOWN WEAKNESSES (author assessment):")
    print("    1. Retrieval is keyword-based — semantically similar but lexically")
    print("       different queries (e.g. 'automobile' vs 'car') will miss.")
    print("    2. Entity normalization depends on LLM consistency — 'my mom' vs")
    print("       'my mother' may produce different subjects.")
    print("    3. Persona consistency is strongly prompted but not mathematically")
    print("       guaranteed — the LLM could still slip under adversarial pressure.")
    print("    4. Decay is time-based only — no semantic decay for emotional states.")
    print()
    print(f"  {report.scenarios_passed}/{len(report.scores)} scenarios fully passed.")
    print("=" * 72)

    return 0 if report.total_failed == 0 else 1


def _avg_dim(report: HarnessReport, attr: str) -> float:
    """Average a dimension score across all scenarios."""
    vals = [getattr(s, attr) for s in report.scores]
    return sum(vals) / len(vals) if vals else 0.0


if __name__ == "__main__":
    sys.exit(main())
