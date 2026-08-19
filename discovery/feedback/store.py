"""Feedback persistence (search memory)."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class FeedbackEntry:
    smiles: str
    axes: dict[str, float] = field(default_factory=dict)
    total: float | None = None
    lower_bound: float | None = None
    uncertainty: float | None = None
    gate_failures: list[str] = field(default_factory=list)
    gate_passed: bool = False
    generation: int = 0
    family: str = ""
    timestamp: str = field(default_factory=lambda: _now())
    official: bool = False
    submitted: bool = False
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class FeedbackStore:
    def __init__(self, path: Path) -> None:
        self.path = path

    def append(self, entry: FeedbackEntry) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry.to_dict(), ensure_ascii=False) + "\n")

    def load_all(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        rows: list[dict[str, Any]] = []
        with self.path.open(encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    rows.append(json.loads(line))
        return rows

    def load_index(self) -> dict[str, dict[str, Any]]:
        index: dict[str, dict[str, Any]] = {}
        for row in self.load_all():
            smiles = row.get("smiles")
            if smiles:
                index[smiles] = row
        return index
