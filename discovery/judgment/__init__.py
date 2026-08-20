"""Local judgment layer for pre-submit decisions.

This module provides LOCAL ranking and decision tools that do NOT produce
official GPU scores. All predictions are empirical priors derived from
the official leaderboard statistics and are clearly labeled as such.

DO NOT auto-submit based on these scores. DO NOT treat them as official.
"""

from discovery.judgment.decision import should_submit, rank_candidates, JudgmentResult
from discovery.judgment.empirical_prior import compute_empirical_prior, EmpiricalPrior
from discovery.judgment.dock import (
    MIN_LOCAL_SEL_KCAL,
    dock_molecule,
    dock_selectivity,
    dock_smiles,
    dual_vina_available,
    vina_available,
)
from discovery.judgment.pocket import check_pocket_pharmacophore

__all__ = [
    "should_submit",
    "rank_candidates",
    "JudgmentResult",
    "compute_empirical_prior",
    "EmpiricalPrior",
    "dock_smiles",
    "dock_molecule",
    "dock_selectivity",
    "vina_available",
    "dual_vina_available",
    "MIN_LOCAL_SEL_KCAL",
    "check_pocket_pharmacophore",
]
