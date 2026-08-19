"""Gate rejection tests."""

from discovery.gates.runner import GateRunner
from discovery.gates import run_gates


def test_reject_invalid_smiles():
    result = run_gates("not_a_molecule!!!")
    assert result.rejected
    assert "invalid_smiles_or_inchi" in result.failures


def test_reject_formula_only():
    result = run_gates("C6H6O2")
    assert result.rejected
    assert "invalid_smiles_or_inchi" in result.failures


def test_reject_mw_over_cap():
    from discovery.config import Config

    cfg = Config(mw_max=100.0)
    runner = GateRunner(cfg)
    # Valid alkane SMILES with explicit branching notation
    result = runner.check("CCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC")
    assert result.rejected
    assert any("mw_over_cap" in f for f in result.failures)


def test_reject_duplicate():
    runner = GateRunner()
    smi = "CCO"
    first = runner.check(smi)
    assert first.passed
    runner.register(first.canonical_smiles or smi)
    second = runner.check(smi)
    assert second.rejected
    assert "duplicate_smiles" in second.failures


def test_reject_pains_or_warhead_if_present():
    runner = GateRunner()
    # benzaldehyde — aldehyde warhead
    result = runner.check("O=Cc1ccccc1")
    assert result.rejected
    assert any("warhead" in f for f in result.failures)
