"""Family isolation tests (rule 8)."""

from discovery.search.families import FamilyScheduler, default_families
from discovery.search.evolution import EvolutionEngine
from discovery.config import Config
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
