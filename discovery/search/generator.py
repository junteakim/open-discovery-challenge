"""Structure generation from scaffold families."""

from __future__ import annotations

import random
from typing import Iterator

from discovery.chemistry.smiles import validate_structure
from discovery.gates.runner import GateRunner
from discovery.search.families import FamilyScheduler, ScaffoldFamily, default_families


class CandidateGenerator:
    def __init__(
        self,
        gate_runner: GateRunner | None = None,
        families: list[ScaffoldFamily] | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.gate_runner = gate_runner or GateRunner()
        self.scheduler = FamilyScheduler(families)
        self.rng = rng or random.Random()

    def seed_batch(self, per_family: int = 5) -> list[tuple[str, str]]:
        """Return (smiles, family_name) pairs that pass gates."""
        out: list[tuple[str, str]] = []
        for family in self.scheduler.families:
            for raw in family.enumerate(limit=per_family * 4):
                gate = self.gate_runner.check(raw)
                if gate.passed and gate.canonical_smiles:
                    self.gate_runner.register(gate.canonical_smiles)
                    out.append((gate.canonical_smiles, family.name))
                    if sum(1 for _, f in out if f == family.name) >= per_family:
                        break
        return out

    def random_variants(
        self,
        family: ScaffoldFamily,
        n: int = 10,
    ) -> Iterator[tuple[str, str]]:
        produced = 0
        attempts = 0
        max_attempts = n * 20
        while produced < n and attempts < max_attempts:
            attempts += 1
            for raw in family.enumerate(limit=1):
                # shuffle r-groups by re-sampling family with shuffled pools
                pass
            choices = {
                k: self.rng.choice(v) for k, v in family.r_groups.items()
            }
            smiles = family.template
            for k, v in choices.items():
                smiles = smiles.replace("{" + k + "}", v)
            if "{" in smiles:
                continue
            gate = self.gate_runner.check(smiles)
            if gate.passed and gate.canonical_smiles:
                self.gate_runner.register(gate.canonical_smiles)
                yield gate.canonical_smiles, family.name
                produced += 1
