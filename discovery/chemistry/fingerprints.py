"""Molecular fingerprints for duplicate and novelty checks."""

from __future__ import annotations

try:
    from rdkit import Chem, DataStructs
    from rdkit.Chem import AllChem
except ImportError:  # pragma: no cover
    Chem = None  # type: ignore[misc, assignment]
    DataStructs = None  # type: ignore[misc, assignment]
    AllChem = None  # type: ignore[misc, assignment]


def morgan_fp(smiles: str, radius: int = 2, n_bits: int = 2048):
    if Chem is None:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return AllChem.GetMorganFingerprintAsBitVect(mol, radius, nBits=n_bits)


def tanimoto(a, b) -> float:
    if DataStructs is None or a is None or b is None:
        return 0.0
    return float(DataStructs.TanimotoSimilarity(a, b))


def max_similarity(smiles: str, library: list[str]) -> float:
    fp = morgan_fp(smiles)
    if fp is None:
        return 0.0
    best = 0.0
    for other in library:
        other_fp = morgan_fp(other)
        if other_fp is not None:
            best = max(best, tanimoto(fp, other_fp))
    return best
