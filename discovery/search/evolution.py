"""Parallel evolutionary search orchestration."""

from __future__ import annotations

import json
import logging
import random
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from discovery.config import Config
from discovery.feedback.store import FeedbackEntry, FeedbackStore
from discovery.gates.runner import GateRunner
from discovery.providers.base import ProviderError, ScoreProvider, ScoreResult
from discovery.providers.replay import ReplayProvider
from discovery.providers.stub import StubProvider
from discovery.scoring import optimization_phase, passes_cutoff, rank_candidates
from discovery.search.families import FamilyScheduler, default_families
from discovery.search.generator import CandidateGenerator
from discovery.search.mutator import mutate_for_axis, select_worst_axis

logger = logging.getLogger(__name__)


@dataclass
class Population:
    family: str
    members: list[ScoreResult] = field(default_factory=list)


@dataclass
class SearchState:
    generation: int = 0
    populations: dict[str, list[str]] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"generation": self.generation, "populations": self.populations}

    @classmethod
    def from_dict(cls, data: dict) -> SearchState:
        return cls(
            generation=int(data.get("generation", 0)),
            populations=dict(data.get("populations") or {}),
        )


class EvolutionEngine:
    def __init__(
        self,
        config: Config | None = None,
        provider: ScoreProvider | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.config = config or Config.from_env()
        self.feedback = FeedbackStore(self.config.paths.feedback)
        self.gate_runner = GateRunner(self.config)
        self.generator = CandidateGenerator(self.gate_runner)
        self.scheduler = FamilyScheduler()
        self.rng = rng or random.Random(42)
        self.provider = provider or self._default_provider()
        self.state = self._load_state()

    def _default_provider(self) -> ScoreProvider:
        replay = ReplayProvider(self.config.paths.feedback)
        if replay.available():
            return replay
        return StubProvider()

    def _load_state(self) -> SearchState:
        path = self.config.paths.state
        if path.exists():
            return SearchState.from_dict(json.loads(path.read_text()))
        return SearchState(populations={f.name: [] for f in default_families()})

    def _save_state(self) -> None:
        path = self.config.paths.state
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.state.to_dict(), indent=2))

    def _record(
        self,
        smiles: str,
        family: str,
        gate_failures: list[str],
        gate_passed: bool,
        score: ScoreResult | None = None,
        generation: int | None = None,
    ) -> None:
        entry = FeedbackEntry(
            smiles=smiles,
            axes=score.axes if score else {},
            total=score.total if score else None,
            lower_bound=score.lower_bound if score else None,
            uncertainty=score.uncertainty if score else None,
            gate_failures=gate_failures,
            gate_passed=gate_passed,
            generation=generation if generation is not None else self.state.generation,
            family=family,
            official=score.official if score else False,
            source=score.source if score else "",
        )
        self.feedback.append(entry)

    def _try_score(self, smiles: str) -> ScoreResult | None:
        try:
            return self.provider.score(smiles)
        except ProviderError as exc:
            logger.debug("Score unavailable for %s: %s", smiles, exc)
            return None

    def seed(
        self,
        per_family: int = 5,
        score_fn: Callable[[str], ScoreResult | None] | None = None,
    ) -> list[tuple[str, str]]:
        score_fn = score_fn or self._try_score
        pairs = self.generator.seed_batch(per_family=per_family)
        for smiles, family in pairs:
            score = score_fn(smiles)
            if score and not passes_cutoff(score):
                self._record(smiles, family, [], True, score)
                continue
            if score and passes_cutoff(score):
                self._record(smiles, family, [], True, score)
                pop = self.state.populations.setdefault(family, [])
                pop.append(smiles)
            else:
                self._record(smiles, family, [], True, None)
        self._save_state()
        return pairs

    def run_generation(
        self,
        score_fn: Callable[[str], ScoreResult | None] | None = None,
    ) -> dict[str, list[ScoreResult]]:
        """One evolutionary generation across all families."""
        score_fn = score_fn or self._try_score
        survivors: dict[str, list[ScoreResult]] = {}

        for family_name in self.scheduler.all_names():
            parents_smiles = self.state.populations.get(family_name, [])
            family_survivors: list[ScoreResult] = []

            for smi in parents_smiles:
                scored = score_fn(smi)
                if scored is None:
                    continue
                self._record(smi, family_name, [], True, scored, self.state.generation)
                if passes_cutoff(scored):
                    family_survivors.append(scored)

            # Promote top parent per family for mutation
            ranked = rank_candidates(family_survivors)
            if not ranked:
                # Seed more if empty
                for smiles, fam in self.generator.random_variants(
                    next(f for f in default_families() if f.name == family_name),
                    n=3,
                ):
                    if fam != family_name:
                        continue
                    gate = self.gate_runner.check(smiles)
                    if not gate.passed:
                        self._record(smiles, family_name, gate.failures, False)
                        continue
                    scored = score_fn(gate.canonical_smiles or smiles)
                    if scored and passes_cutoff(scored):
                        family_survivors.append(scored)
                        self._record(gate.canonical_smiles or smiles, family_name, [], True, scored)
                ranked = rank_candidates(family_survivors)

            if not ranked:
                survivors[family_name] = []
                continue

            parent = ranked[0]
            phase = optimization_phase(parent)
            axis = select_worst_axis(parent, phase)
            children: list[ScoreResult] = [parent]

            for child_smi in mutate_for_axis(parent.smiles, axis, self.rng):
                gate = self.gate_runner.check(child_smi)
                if not gate.passed or not gate.canonical_smiles:
                    self._record(child_smi, family_name, gate.failures, False)
                    continue
                self.gate_runner.register(gate.canonical_smiles)
                scored = score_fn(gate.canonical_smiles)
                if scored is None:
                    self._record(gate.canonical_smiles, family_name, [], True, None)
                    continue
                self._record(
                    gate.canonical_smiles,
                    family_name,
                    [],
                    True,
                    scored,
                    self.state.generation + 1,
                )
                if passes_cutoff(scored):
                    children.append(scored)

            survivors[family_name] = rank_candidates(children)[:5]
            self.state.populations[family_name] = [s.smiles for s in survivors[family_name]]

        self.state.generation += 1
        self._save_state()
        return survivors

    def run(
        self,
        generations: int = 3,
        per_family: int = 5,
        score_fn: Callable[[str], ScoreResult | None] | None = None,
    ) -> dict[str, list[ScoreResult]]:
        if self.state.generation == 0 and not any(self.state.populations.values()):
            self.seed(per_family=per_family, score_fn=score_fn)
        results: dict[str, list[ScoreResult]] = {}
        for _ in range(generations):
            results = self.run_generation(score_fn=score_fn)
        return results
