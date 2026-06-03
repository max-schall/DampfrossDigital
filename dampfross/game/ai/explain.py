"""
Structured decision-result objects for tracing and debugging AI choices.

Every public decision method in the AI services returns a DecisionResult.
The result is self-contained: it can be printed, logged, or inspected in
tests without depending on any game state.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Candidate:
    """One option considered by the AI during a decision."""
    label: str                    # human-readable description
    action: Any                   # the concrete action value
    score: float
    factors: dict = field(default_factory=dict)  # name → contribution


@dataclass
class DecisionResult:
    """The outcome of one AI decision step."""
    phase: str                    # "build" | "participate" | "route" | "cooperate"
    chosen: Any                   # the selected action (None = pass / no-op)
    chosen_score: float = 0.0
    candidates: list[Candidate] = field(default_factory=list)
    tiebreak: str = ""            # explanation when scores were equal
    note: str = ""                # free-form context

    def best_factors(self) -> dict:
        """Return the score factors of the chosen candidate, or empty dict."""
        for c in self.candidates:
            if c.action == self.chosen:
                return c.factors
        return {}

    def __str__(self) -> str:
        lines = [
            f"[AI:{self.phase}] chosen={self.chosen!r}  score={self.chosen_score:.2f}",
        ]
        if self.note:
            lines.append(f"  note: {self.note}")
        for c in self.candidates[:5]:
            marker = "►" if c.action == self.chosen else " "
            lines.append(f"  {marker} {c.label:<40}  {c.score:+.2f}  {c.factors}")
        if self.tiebreak:
            lines.append(f"  tiebreak: {self.tiebreak}")
        return "\n".join(lines)
