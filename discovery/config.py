"""Runtime configuration and challenge constants."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_BASE_URL = "https://final-bench-open-discovery-challenge.hf.space"
DEFAULT_SEASON = 1
SCORE_CUTOFF = 60.0  # candidates with effective score <= 60 are excluded

AXIS_WEIGHTS = {
    "activity": 30,
    "binding": 20,
    "selectivity": 20,
    "admet": 15,
    "novelty": 10,
    "synthesis": 5,
}

CORE_AXES = ("activity", "binding", "selectivity")
SECONDARY_AXES = ("admet", "novelty", "synthesis")


@dataclass
class Paths:
    root: Path = field(default_factory=lambda: Path.cwd())
    feedback: Path = field(init=False)
    state: Path = field(init=False)
    candidates: Path = field(init=False)

    def __post_init__(self) -> None:
        data = self.root / "data"
        self.feedback = data / "feedback.jsonl"
        self.state = data / "search_state.json"
        self.candidates = data / "candidates.jsonl"


@dataclass
class Config:
    base_url: str = DEFAULT_BASE_URL
    season: int = DEFAULT_SEASON
    mw_max: float = 550.0
    heavy_max: int = 45
    hf_token: str | None = None
    challenge_token: str | None = None
    paths: Paths = field(default_factory=Paths)

    @classmethod
    def from_env(cls, root: Path | None = None) -> Config:
        root = root or Path.cwd()
        return cls(
            base_url=os.environ.get("FINALBENCH_BASE_URL", DEFAULT_BASE_URL).rstrip("/"),
            season=int(os.environ.get("FINALBENCH_SEASON", str(DEFAULT_SEASON))),
            hf_token=os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN"),
            challenge_token=os.environ.get("CHALLENGE_TOKEN"),
            paths=Paths(root=root),
        )
