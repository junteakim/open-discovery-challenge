"""Gate result model."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class GateResult:
    passed: bool
    failures: list[str] = field(default_factory=list)
    canonical_smiles: str | None = None

    @property
    def rejected(self) -> bool:
        return not self.passed
