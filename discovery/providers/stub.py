"""Stub provider — refuses to invent official FINAL-Bench scores."""

from __future__ import annotations

from discovery.providers.base import ProviderError, ScoreResult


class StubProvider:
    name = "stub"

    def available(self) -> bool:
        return True

    def score(self, smiles: str) -> ScoreResult:
        raise ProviderError(
            "Stub provider refuses to fake official FINAL-Bench scores. "
            "Set HF_TOKEN / CHALLENGE_TOKEN for FinalBenchProvider, "
            "or use ReplayProvider with prior feedback.jsonl entries."
        )
