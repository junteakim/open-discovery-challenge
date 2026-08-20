"""Docking hook for PfDHODH (LOCAL scores only, not official GPU).

If vina/smina is available, dock generated conformers.
If not available, return unavailable (do NOT fake kcal scores).
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem
except ImportError:  # pragma: no cover
    Chem = None
    AllChem = None


def check_docking_available() -> tuple[bool, str | None]:
    """
    Check if docking software is available.
    
    Returns:
        (available, path_or_reason)
    """
    # Check for vina
    vina_path = shutil.which("vina")
    if vina_path:
        return True, vina_path
    
    # Check for smina
    smina_path = shutil.which("smina")
    if smina_path:
        return True, smina_path
    
    return False, "no_vina_or_smina_in_path"


def dock_molecule(
    smiles: str,
    receptor_pdbqt: Path | None = None,
) -> dict[str, any]:
    """
    Dock molecule into PfDHODH pocket if docking software available.
    
    Args:
        smiles: SMILES to dock
        receptor_pdbqt: Path to prepared receptor PDBQT (optional)
    
    Returns:
        Dict with:
            - available: bool
            - affinity: float | None (kcal/mol, more negative = better)
            - reason: str
            - source: str (always "local_docking_not_official")
    """
    available, binary = check_docking_available()
    
    if not available:
        return {
            "available": False,
            "affinity": None,
            "reason": binary or "docking_unavailable",
            "source": "local_docking_not_official",
        }
    
    # If we get here, vina/smina exists but we need a prepared receptor
    # For now, return unavailable since we don't have the receptor prepared
    # In a full implementation, we would:
    # 1. Generate 3D conformer from SMILES
    # 2. Convert to PDBQT
    # 3. Run vina/smina with prepared receptor
    # 4. Parse output affinity
    
    return {
        "available": False,
        "affinity": None,
        "reason": "receptor_not_prepared_implementation_placeholder",
        "source": "local_docking_not_official",
        "note": "Docking binary found but receptor prep not implemented",
    }


def estimate_binding_potential(smiles: str) -> float:
    """
    Estimate LOCAL binding potential without actual docking.
    
    This is a very rough heuristic based on MW, logP, H-bonds.
    NOT an official score, NOT actual binding affinity.
    
    Returns:
        Rough score 0-20 (higher = potentially better binding)
    """
    if Chem is None:
        return 0.0
    
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return 0.0
    
    try:
        from rdkit.Chem import Descriptors, Crippen, Lipinski
        
        mw = Descriptors.MolWt(mol)
        logp = Crippen.MolLogP(mol)
        hba = Lipinski.NumHAcceptors(mol)
        hbd = Lipinski.NumHDonors(mol)
        rotatable = Descriptors.NumRotatableBonds(mol)
        
        # Very rough heuristic (NOT binding affinity)
        score = 0.0
        
        # Prefer MW 300-500 (typical drug-like)
        if 300 <= mw <= 500:
            score += 5.0
        elif 250 <= mw <= 550:
            score += 3.0
        
        # Prefer moderate logP (2-4)
        if 2 <= logp <= 4:
            score += 5.0
        elif 1 <= logp <= 5:
            score += 3.0
        
        # H-bonds (need some but not too many)
        hbond_total = hba + hbd
        if 3 <= hbond_total <= 6:
            score += 5.0
        elif 2 <= hbond_total <= 8:
            score += 3.0
        
        # Prefer some flexibility but not too much
        if 3 <= rotatable <= 8:
            score += 5.0
        elif 2 <= rotatable <= 10:
            score += 2.0
        
        return min(score, 20.0)
    
    except Exception:
        return 0.0
