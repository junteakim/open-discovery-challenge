"""Replay scores from persisted feedback (search memory)."""

from __future__ import annotations

from pathlib import Path

from discovery.feedback.store import FeedbackStore
from discovery.providers.base import ProviderError, ScoreResult


class ReplayProvider:
    name = "replay"

    def __init__(self, feedback_path: Path) -> None:
        self.store = FeedbackStore(feedback_path)
        self._cache = self.store.load_index()

    def available(self) -> bool:
        return bool(self._cache)

    def score(self, smiles: str) -> ScoreResult:
        entry = self._cache.get(smiles)
        if entry is None or entry.get("total") is None:
            raise ProviderError(f"No replay score for {smiles}")
        return ScoreResult(
            smiles=smiles,
            axes=entry.get("axes") or {},
            total=float(entry["total"]),
            lower_bound=entry.get("lower_bound"),
            uncertainty=entry.get("uncertainty"),
            source="replay",
            official=bool(entry.get("official", False)),
        )

    def refresh(self) -> None:
        self._cache = self.store.load_index()
