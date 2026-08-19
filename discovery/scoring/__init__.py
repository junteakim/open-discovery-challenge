"""Scoring utilities: cutoff, ranking, phase detection."""

from __future__ import annotations

from discovery.config import CORE_AXES, SCORE_CUTOFF, SECONDARY_AXES
from discovery.providers.base import ScoreResult


def effective_score(result: ScoreResult) -> float:
    return result.effective_score()


def passes_cutoff(result: ScoreResult, cutoff: float = SCORE_CUTOFF) -> bool:
    return effective_score(result) > cutoff


def rank_candidates(candidates: list[ScoreResult]) -> list[ScoreResult]:
    """Prefer higher lower-bound; tie-break by mean total (rule 4)."""
    return sorted(
        candidates,
        key=lambda r: (effective_score(r), r.total),
        reverse=True,
    )


def core_competitive(result: ScoreResult, fraction: float = 0.55) -> bool:
    """True when 70-pt core axes sum to a competitive fraction of their max."""
    axes = result.axes
    core_sum = sum(axes.get(a, 0.0) for a in CORE_AXES)
    core_max = 30 + 20 + 20
    return core_sum >= fraction * core_max


def optimization_phase(result: ScoreResult) -> str:
    """Rule 2 then 5: core first, ADMET/synthesis after core is competitive."""
    return "secondary" if core_competitive(result) else "core"


def worst_axis(result: ScoreResult, phase: str | None = None) -> str:
    """Rule 7: mutate only the worst-scoring axis of a surviving parent."""
    phase = phase or optimization_phase(result)
    pool = list(SECONDARY_AXES) if phase == "secondary" else list(CORE_AXES)
    weights = {"activity": 30, "binding": 20, "selectivity": 20, "admet": 15, "novelty": 10, "synthesis": 5}

    def deficit(axis: str) -> float:
        raw = result.axes.get(axis, 0.0)
        return raw / weights[axis]

    return min(pool, key=deficit)
