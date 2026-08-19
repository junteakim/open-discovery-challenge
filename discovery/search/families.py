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
# Updated to target MW 450-550 competitive band (season 1 median 67.6 in 500-550 band)
_AMIDES = ["C(=O)NCCC", "C(=O)NC(C)C", "C(=O)NCCOC", "C(=O)N(CC)CC", "C(=O)NCCc1ccccc1"]
_AROMATIC = ["c1ccc(OC)cc1", "c1ccc(C(F)(F)F)cc1", "c1ccc(Cl)c(OC)c1", "c1ccc2ccccc2c1", "c1ccc(OCc2ccccc2)cc1"]
_ALIPHATIC = ["CCC", "CC(C)C", "CCOC", "CC(C)CC", "CCCN", "CCOc1ccccc1"]
_HETEROCYCLES = ["c1ncc(C)cn1", "c1ccc(C)nc1", "c1cc(OC)ccn1", "c1ccc2occc2c1", "c1cc(Cl)ccn1"]
_LINKERS = ["CC(=O)", "CCN(C)C", "CCOC", "C(=O)NCC", "CCOc1ccccc1"]
_BIARYL = ["c1ccc(c1)c1ccccc1", "c1ccc(c1)c1ccc(OC)cc1", "c1ccc(c1)c1ccc(F)cc1"]


def default_families() -> list[ScaffoldFamily]:
    return [
        ScaffoldFamily(
            name="benzimidazole_amide",
            template="c1ccc2[nH]c({R1})nc2c1{R2}",
            r_groups={"R1": _AMIDES, "R2": _AROMATIC + _BIARYL},
        ),
        ScaffoldFamily(
            name="quinazoline_urea",
            template="c1ccc2c(c1)nc({R1})nc2{R2}",
            r_groups={"R1": ["NC(=O)NCC", "NC(=O)NCCC", "NC(=O)NC(C)C", "NC(=O)NCCc1ccccc1"], "R2": _HETEROCYCLES + _AROMATIC},
        ),
        ScaffoldFamily(
            name="pyrimidine_sulfonamide",
            template="c1nc({R1})nc({R2})c1{S}",
            r_groups={
                "R1": _ALIPHATIC + ["c1ccccc1"],
                "R2": _AROMATIC[:3],
                "S": ["S(=O)(=O)NCC", "S(=O)(=O)NCCC", "S(=O)(=O)NCc1ccccc1"],
            },
        ),
        ScaffoldFamily(
            name="indole_carboxamide",
            template="c1ccc2[nH]c({R1})cc2c1{R2}",
            r_groups={"R1": _AMIDES, "R2": _AROMATIC + _BIARYL},
        ),
        ScaffoldFamily(
            name="triazine_aniline",
            template="c1nc({R1})nc({R2})n1{R3}",
            r_groups={
                "R1": ["Nc1ccc(OC)cc1", "Nc1ccc(Cl)cc1", "Nc1ccc(C)cc1"],
                "R2": _HETEROCYCLES[:3] + _AROMATIC[:2],
                "R3": _LINKERS[:3],
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
