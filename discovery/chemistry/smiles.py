"""SMILES / InChI validation and canonicalization."""

from __future__ import annotations

import re

try:
    from rdkit import Chem
except ImportError:  # pragma: no cover
    Chem = None  # type: ignore[misc, assignment]

FORMULA_RE = re.compile(r"^[A-Z][a-z]?\d*([A-Z][a-z]?\d*)*$")


def validate_structure(structure: str) -> tuple[bool, str | None]:
    """Return (valid, canonical_smiles_or_none)."""
    if not structure or not structure.strip():
        return False, None
    text = structure.strip()
    if is_formula_only(text):
        return False, None
    if Chem is None:
        return False, None
    mol = Chem.MolFromSmiles(text)
    if mol is None:
        mol = Chem.MolFromInchi(text)
    if mol is None:
        return False, None
    try:
        Chem.SanitizeMol(mol)
    except Exception:
        return False, None
    return True, canonicalize(mol)


def canonicalize(mol_or_smiles) -> str | None:
    if Chem is None:
        return None
    if isinstance(mol_or_smiles, str):
        mol = Chem.MolFromSmiles(mol_or_smiles)
        if mol is None:
            return None
    else:
        mol = mol_or_smiles
    return Chem.MolToSmiles(mol, canonical=True)


def is_formula_only(text: str) -> bool:
    """Reject bare molecular formulas without explicit connectivity."""
    stripped = text.strip()
    if not stripped:
        return True
    # SMILES/InChI markers
    if any(ch in stripped for ch in "()[]=#@\\/+-."):
        return False
    if stripped.startswith("InChI="):
        return False
    if any(c.islower() for c in stripped):
        return False
    # Hill formulas use digit subscripts (e.g. C6H6O2); bare CCO is SMILES, not a formula.
    if not re.search(r"\d", stripped):
        return False
    return bool(FORMULA_RE.fullmatch(stripped))
