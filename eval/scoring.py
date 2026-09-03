"""Structured evaluation scoring model for the companion-AI memory system.

Provides multi-dimensional scoring with named failure classes instead of
flat pass/fail counts. Each scenario produces an EvalScore with:
  - Per-dimension scores (0.0-1.0)
  - Named failure tags
  - Overall pass/fail based on configurable thresholds
"""

from dataclasses import dataclass, field


# ── Failure Class Definitions ────────────────────────────────────────────────
# Failure class taxonomy for companion-AI domain.

FAILURE_CLASSES = {
    "memory_miss": "System failed to retrieve a relevant stored fact when queried.",
    "memory_hallucination": "System claimed a fact not present in the memory store.",
    "contradiction_leak": "A superseded fact appeared in active retrieval results.",
    "duplicate_stored": "Same fact stored twice with different IDs.",
    "decay_failure": "A stale plan/event was not expired, or an identity fact was incorrectly expired.",
    "persona_drift": "Response broke character or flattened to generic assistant tone.",
    "supersession_failure": "Contradiction was not handled — both old and new facts remained active.",
}


@dataclass
class EvalScore:
    """Structured evaluation score for a single scenario."""

    scenario_name: str
    memory_recall_accuracy: float = 1.0      # % of expected facts retrieved
    contradiction_handling: float = 1.0       # % of contradictions correctly superseded
    duplicate_prevention: float = 1.0         # % of duplicates correctly detected
    decay_accuracy: float = 1.0              # % of decay operations correct
    persona_consistency: float = 1.0          # persona checks passed ratio
    failure_tags: list[str] = field(default_factory=list)
    assertions_passed: int = 0
    assertions_failed: int = 0
    details: list[str] = field(default_factory=list)

    @property
    def overall_pass(self) -> bool:
        return self.assertions_failed == 0

    @property
    def pass_rate(self) -> float:
        total = self.assertions_passed + self.assertions_failed
        return (self.assertions_passed / total * 100) if total > 0 else 0.0

    def to_dict(self) -> dict:
        return {
            "scenario_name": self.scenario_name,
            "overall_pass": self.overall_pass,
            "pass_rate": f"{self.pass_rate:.1f}%",
            "memory_recall_accuracy": self.memory_recall_accuracy,
            "contradiction_handling": self.contradiction_handling,
            "duplicate_prevention": self.duplicate_prevention,
            "decay_accuracy": self.decay_accuracy,
            "persona_consistency": self.persona_consistency,
            "failure_tags": self.failure_tags,
            "assertions": f"{self.assertions_passed}/{self.assertions_passed + self.assertions_failed}",
        }


@dataclass
class HarnessReport:
    """Aggregated report across all scenarios."""

    scores: list[EvalScore] = field(default_factory=list)

    @property
    def total_passed(self) -> int:
        return sum(s.assertions_passed for s in self.scores)

    @property
    def total_failed(self) -> int:
        return sum(s.assertions_failed for s in self.scores)

    @property
    def total_assertions(self) -> int:
        return self.total_passed + self.total_failed

    @property
    def overall_pass_rate(self) -> float:
        return (self.total_passed / self.total_assertions * 100) if self.total_assertions > 0 else 0.0

    @property
    def scenarios_passed(self) -> int:
        return sum(1 for s in self.scores if s.overall_pass)

    @property
    def all_failure_tags(self) -> list[str]:
        tags = []
        for s in self.scores:
            tags.extend(s.failure_tags)
        return tags

    def failure_tag_summary(self) -> dict[str, int]:
        """Count occurrences of each failure class."""
        counts: dict[str, int] = {}
        for tag in self.all_failure_tags:
            counts[tag] = counts.get(tag, 0) + 1
        return counts
