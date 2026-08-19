"""Score provider protocol and result model."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


class ProviderError(Exception):
    """Raised when a provider cannot produce official scores."""


@dataclass
class ScoreResult:
    smiles: str
    axes: dict[str, float]
    total: float
    lower_bound: float | None = None
    uncertainty: float | None = None
    source: str = "unknown"
    official: bool = False

    def effective_score(self) -> float:
        """Conservative score for cutoff and ranking (rule 0, 4)."""
        if self.lower_bound is not None:
            return self.lower_bound
        return self.total

    @property
    def passes_cutoff(self) -> bool:
        from discovery.config import SCORE_CUTOFF

        return self.effective_score() > SCORE_CUTOFF


class ScoreProvider(Protocol):
    name: str

    def available(self) -> bool: ...

    def score(self, smiles: str) -> ScoreResult:
        """Return official or replayed score. Raises ProviderError if unavailable."""
