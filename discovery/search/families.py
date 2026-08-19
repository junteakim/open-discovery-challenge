"""Scaffold families for parallel evolutionary search."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterator

# Programmatic scaffold templates — distinct cores, not DSM265 decoration.
# Placeholders: {R1}, {R2}, {R3} replaced with validated substituent SMILES fragments.


@dataclass(frozen=True)
class ScaffoldFamily:
    name: str
    template: str
    r_groups: dict[str, list[str]] = field(default_factory=dict)
    generation: int = 0

    def enumerate(self, limit: int | None = None) -> Iterator[str]:
        """Cartesian product of R-groups stitched into template."""
        keys = list(self.r_groups.keys())
        if not keys:
            yield self.template
            return

        def rec(idx: int, current: dict[str, str]) -> Iterator[str]:
            if idx >= len(keys):
                smiles = self.template
                for k, v in current.items():
                    smiles = smiles.replace("{" + k + "}", v)
                if "{" not in smiles:
                    yield smiles
                return
            key = keys[idx]
            for frag in self.r_groups[key]:
                current[key] = frag
                yield from rec(idx + 1, current)

        count = 0
        for smi in rec(0, {}):
            yield smi
            count += 1
            if limit is not None and count >= limit:
                break


# Substituent pools (fragments attach at attachment points in templates)
_AMIDES = ["C(=O)N", "C(=O)NC", "C(=O)NCC", "C(=O)N(C)C"]
_AROMATIC = ["c1ccccc1", "c1ccc(F)cc1", "c1ccc(OC)cc1", "c1ccncc1"]
_ALIPHATIC = ["C", "CC", "C(C)C", "CCO", "CCN"]
_HETEROCYCLES = ["c1ncccc1", "c1ccoc1", "c1cscn1", "c1cncnc1"]


def default_families() -> list[ScaffoldFamily]:
    return [
        ScaffoldFamily(
            name="benzimidazole_amide",
            template="c1ccc2[nH]c({R1})nc2c1{R2}",
            r_groups={"R1": _AMIDES, "R2": _AROMATIC[:3]},
        ),
        ScaffoldFamily(
            name="quinazoline_urea",
            template="c1ccc2c(c1)nc({R1})nc2{R2}",
            r_groups={"R1": ["NC(=O)N", "NC(=O)NC", "NC(=O)NCC"], "R2": _HETEROCYCLES[:3]},
        ),
        ScaffoldFamily(
            name="pyrimidine_sulfonamide",
            template="c1nc({R1})nc({R2})c1{S}",
            r_groups={
                "R1": _ALIPHATIC[:3],
                "R2": _AROMATIC[:2],
                "S": ["S(=O)(=O)N", "S(=O)(=O)NC"],
            },
        ),
        ScaffoldFamily(
            name="indole_carboxamide",
            template="c1ccc2[nH]c({R1})cc2c1{R2}",
            r_groups={"R1": _AMIDES[:3], "R2": _ALIPHATIC[:3]},
        ),
        ScaffoldFamily(
            name="triazine_aniline",
            template="c1nc({R1})nc({R2})n1{R3}",
            r_groups={
                "R1": ["N", "Nc1ccccc1"],
                "R2": _HETEROCYCLES[:2],
                "R3": ["C(=O)N", "C(=O)NC"],
            },
        ),
    ]


class FamilyScheduler:
    """Round-robin across families so none monopolizes the queue (rule 8)."""

    def __init__(self, families: list[ScaffoldFamily] | None = None) -> None:
        self.families = families or default_families()
        self._cursor = 0

    def next_family(self) -> ScaffoldFamily:
        fam = self.families[self._cursor % len(self.families)]
        self._cursor += 1
        return fam

    def all_names(self) -> list[str]:
        return [f.name for f in self.families]
