"""Prohibited covalent warhead SMARTS."""

from __future__ import annotations

try:
    from rdkit import Chem
except ImportError:  # pragma: no cover
    Chem = None

# Michael acceptors, epoxides, aldehydes, acyl halides, isocyanates, etc.
WARHEAD_SMARTS = [
    ("michael_acceptor", "[C,c]=[C,c]-[C,S,O,N]=[O,N]"),
    ("aldehyde", "[CH1](=O)"),
    ("epoxide", "C1OC1"),
    ("acyl_halide", "C(=O)[Cl,Br,I]"),
    ("isocyanate", "N=C=O"),
    ("sulfonyl_fluoride", "S(=O)(=O)F"),
    ("chloroacetamide", "ClCC(=O)N"),
    ("nitrile_aldehyde", "N#C[C,c]=O"),
]

_PATTERNS: list[tuple[str, object]] | None = None


def _patterns() -> list[tuple[str, object]]:
    global _PATTERNS
    if _PATTERNS is None and Chem is not None:
        _PATTERNS = []
        for name, smarts in WARHEAD_SMARTS:
            pat = Chem.MolFromSmarts(smarts)
            if pat is not None:
                _PATTERNS.append((name, pat))
    return _PATTERNS or []


def warhead_matches(smiles: str) -> list[str]:
    if Chem is None:
        return []
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return ["invalid_structure"]
    hits: list[str] = []
    for name, pat in _patterns():
        if mol.HasSubstructMatch(pat):
            hits.append(name)
    return hits
