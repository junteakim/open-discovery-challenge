"""Axis-targeted mutation (rule 7)."""

from __future__ import annotations

import random
from typing import Callable

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem
except ImportError:  # pragma: no cover
    Chem = None
    AllChem = None

from discovery.chemistry.smiles import canonicalize
from discovery.scoring import worst_axis
from discovery.providers.base import ScoreResult

# SMIRKS-style transforms keyed by axis deficit
_MUTATIONS: dict[str, list[str]] = {
    "activity": [
        "[*:1]>>[*:1]N",  # add nitrogen (permeability proxy)
        "[c:1]>>[c:1]F",  # fluorination
        "[*:1]>>[*:1]C(C)C",  # lipophilic branch
    ],
    "binding": [
        "[*:1]>>[*:1]C(=O)N",  # amide H-bond
        "[*:1]>>[*:1]O",  # hydroxyl
        "[*:1]>>[*:1]C#N",  # nitrile acceptor
    ],
    "selectivity": [
        "[c:1]>>[c:1]Cl",  # halogen swap
        "[*:1]>>[*:1]OC",  # polar mask
        "[*:1]>>[*:1]C(F)(F)F",  # CF3 bulk
    ],
    "admet": [
        "[*:1]C(F)(F)F>>[*:1]",  # remove CF3
        "[*:1]>>[*:1]O",  # add polarity
        "[c:1]F>>[c:1]",  # defluorinate
    ],
    "novelty": [
        "[c:1]>>[c:1]C",  # methyl hop
        "[*:1]>>[*:1]C(C)C",  # branch change
        "[*:1]>>[*:1]N(C)C",  # dimethylamine
    ],
    "synthesis": [
        "[*:1]C(C)(C)C>>[*:1]C",  # simplify tert-butyl
        "[*:1]C(F)(F)F>>[*:1]",  # remove CF3
        "[*:1]S(=O)(=O)[*:2]>>[*:1][*:2]",  # remove sulfonyl
    ],
}


def mutate_for_axis(smiles: str, axis: str, rng: random.Random | None = None) -> list[str]:
    """Return mutated SMILES candidates for the given weak axis."""
    if Chem is None:
        return []
    rng = rng or random.Random()
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return []

    rxns = _MUTATIONS.get(axis, _MUTATIONS["novelty"])
    rxns_list = list(rxns)
    rng.shuffle(rxns_list)
    products: list[str] = []
    for smirks in rxns_list[:3]:
        try:
            rxn = AllChem.ReactionFromSmarts(smirks)
            if rxn is None:
                continue
            outcomes = rxn.RunReactants((mol,))
            for outcome in outcomes:
                for prod in outcome:
                    try:
                        Chem.SanitizeMol(prod)
                        smi = canonicalize(prod)
                        if smi and smi != smiles:
                            products.append(smi)
                    except Exception:
                        continue
        except Exception:
            continue
    return list(dict.fromkeys(products))


def mutate_parent(
    parent: ScoreResult,
    phase: str | None = None,
    rng: random.Random | None = None,
) -> tuple[str, list[str]]:
    """Pick worst axis and return (axis, mutated_smiles)."""
    axis = worst_axis(parent, phase)
    variants = mutate_for_axis(parent.smiles, axis, rng)
    return axis, variants


def select_worst_axis(parent: ScoreResult, phase: str | None = None) -> str:
    return worst_axis(parent, phase)
