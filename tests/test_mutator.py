"""Worst-axis mutation selection (rule 7)."""

from discovery.providers.base import ScoreResult
from discovery.scoring import optimization_phase, worst_axis
from discovery.search.mutator import mutate_parent, select_worst_axis


def _result(**axes) -> ScoreResult:
    defaults = {
        "activity": 20.0,
        "binding": 15.0,
        "selectivity": 15.0,
        "admet": 10.0,
        "novelty": 7.0,
        "synthesis": 4.0,
    }
    defaults.update(axes)
    total = sum(defaults.values())
    return ScoreResult(smiles="c1ccccc1C(=O)N", axes=defaults, total=total)


def test_worst_core_axis_is_binding_when_lowest():
    r = _result(binding=5.0, activity=25.0, selectivity=18.0)
    assert select_worst_axis(r, "core") == "binding"
    assert worst_axis(r, "core") == "binding"


def test_worst_core_axis_activity():
    r = _result(activity=5.0, binding=18.0, selectivity=18.0)
    assert worst_axis(r, "core") == "activity"


def test_secondary_phase_when_core_competitive():
    r = _result(activity=26.0, binding=18.0, selectivity=17.0, admet=3.0)
    assert optimization_phase(r) == "secondary"
    assert worst_axis(r) == "admet"


def test_mutate_parent_returns_axis_and_variants():
    r = _result(activity=5.0, binding=18.0, selectivity=18.0)
    axis, variants = mutate_parent(r, phase="core")
    assert axis == "activity"
    assert isinstance(variants, list)
