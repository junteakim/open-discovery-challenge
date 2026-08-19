"""Lower-bound ranking tests (rule 4)."""

from discovery.providers.base import ScoreResult
from discovery.scoring import rank_candidates


def test_prefer_higher_lower_bound_over_higher_mean():
    high_mean = ScoreResult(
        smiles="A",
        axes={},
        total=80.0,
        lower_bound=55.0,
        uncertainty=25.0,
    )
    conservative = ScoreResult(
        smiles="B",
        axes={},
        total=70.0,
        lower_bound=65.0,
        uncertainty=5.0,
    )
    ranked = rank_candidates([high_mean, conservative])
    assert ranked[0].smiles == "B"
    assert ranked[1].smiles == "A"


def test_tiebreak_by_total():
    a = ScoreResult(smiles="A", axes={}, total=70.0, lower_bound=65.0)
    b = ScoreResult(smiles="B", axes={}, total=68.0, lower_bound=65.0)
    ranked = rank_candidates([b, a])
    assert ranked[0].smiles == "A"
