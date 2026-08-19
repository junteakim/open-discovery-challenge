"""Score cutoff (rule 0) tests."""

from discovery.config import SCORE_CUTOFF
from discovery.providers.base import ScoreResult
from discovery.scoring import effective_score, passes_cutoff


def test_drop_at_or_below_60_point_estimate():
    r = ScoreResult(smiles="CCO", axes={}, total=60.0)
    assert not passes_cutoff(r)
    assert effective_score(r) == 60.0


def test_drop_at_55():
    r = ScoreResult(smiles="CCO", axes={}, total=55.0)
    assert not passes_cutoff(r)


def test_pass_above_60():
    r = ScoreResult(smiles="CCO", axes={}, total=61.0)
    assert passes_cutoff(r)


def test_cutoff_uses_lower_bound_when_uncertainty():
    # Mean 72 but lower bound 58 → excluded
    r = ScoreResult(
        smiles="CCO",
        axes={},
        total=72.0,
        lower_bound=58.0,
        uncertainty=14.0,
    )
    assert effective_score(r) == 58.0
    assert not passes_cutoff(r)


def test_pass_when_lower_bound_above_cutoff():
    r = ScoreResult(
        smiles="CCO",
        axes={},
        total=75.0,
        lower_bound=62.0,
        uncertainty=13.0,
    )
    assert passes_cutoff(r)


def test_cutoff_constant():
    assert SCORE_CUTOFF == 60.0
