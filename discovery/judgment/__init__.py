"""Local judgment layer for pre-submit decisions.

This module provides LOCAL ranking and decision tools that do NOT produce
official GPU scores. All predictions are empirical priors derived from
the official leaderboard statistics and are clearly labeled as such.

DO NOT auto-submit based on these scores. DO NOT treat them as official.
"""

from discovery.judgment.decision import should_submit, JudgmentResult
from discovery.judgment.empirical_prior import compute_empirical_prior, EmpiricalPrior

__all__ = [
    "should_submit",
    "JudgmentResult",
    "compute_empirical_prior",
    "EmpiricalPrior",
]
