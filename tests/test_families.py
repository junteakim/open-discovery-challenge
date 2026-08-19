"""Family isolation tests (rule 8)."""

from discovery.search.families import FamilyScheduler, default_families
from discovery.search.evolution import EvolutionEngine
from discovery.config import Config
from discovery.gates.runner import GateRunner
from pathlib import Path
import tempfile


def test_scheduler_round_robin():
    sched = FamilyScheduler()
    names = [sched.next_family().name for _ in range(10)]
    unique = sched.all_names()
    assert len(unique) >= 3
    # Each family appears in first len(families) picks
    first_round = names[: len(unique)]
    assert len(set(first_round)) == len(unique)


def test_separate_populations_per_family():
    with tempfile.TemporaryDirectory() as tmp:
        cfg = Config.from_env(Path(tmp))
        engine = EvolutionEngine(cfg)
        pops = engine.state.populations
        for fam in default_families():
            assert fam.name in pops
            assert isinstance(pops[fam.name], list)


def test_families_generate_distinct_names():
    families = default_families()
    names = {f.name for f in families}
    assert len(names) == len(families)


def test_families_produce_competitive_mw():
    """Families should produce at least one gate-passed seed with MW ≥ 400."""
    from discovery.scoring.prior import compute_mw
    
    with tempfile.TemporaryDirectory() as tmp:
        cfg = Config.from_env(Path(tmp))
        runner = GateRunner(cfg)
        
        families = default_families()
        found_competitive = False
        
        for family in families:
            for smiles in family.enumerate(limit=20):
                gate = runner.check(smiles)
                if gate.passed and gate.canonical_smiles:
                    mw = compute_mw(gate.canonical_smiles)
                    if mw and mw >= 400:
                        found_competitive = True
                        break
            if found_competitive:
                break
        
        assert found_competitive, "No family produced a gate-passed seed with MW ≥ 400"

