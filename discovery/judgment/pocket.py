"""PfDHODH pharmacophore check (LOCAL 2D SMARTS/Lipinski, not pocket docking).

This is a 2D pharmacophore filter based on DSM265 literature patterns.
For actual 3D docking into PfDHODH pocket, see discovery/judgment/dock.py.

PfDHODH (PDB 5TBO / DSM265 binding site):
- Key H-bond residues: HIS185, ARG265
- Hydrophobic pocket for aryl/aniline tail
- Requires: aromatic ring, H-bond acceptor (for HIS185/ARG265), 
  H-bond donor OR basic N, not just alkyl chains

This is a LOCAL 2D filter, NOT an official scoring function.
"""

from __future__ import annotations

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors, Lipinski, AllChem
except ImportError:  # pragma: no cover
    Chem = None
    Descriptors = None
    Lipinski = None
    AllChem = None


def check_pharmacophore(smiles: str) -> tuple[bool, str, dict[str, int]]:
    """
    Check if molecule matches PfDHODH pharmacophore requirements.
    
    Requirements (based on DSM265/literature):
    1. At least one aromatic ring
    2. At least one H-bond acceptor (N/O for HIS185/ARG265 interaction)
    3. At least one H-bond donor OR basic nitrogen
    4. Not just alkyl chains (must have heteroatoms)
    
    Returns:
        (passes, reason, feature_counts)
        
    This is a LOCAL pharmacophore check, NOT official scoring.
    """
    if Chem is None:
        return False, "rdkit_unavailable", {}
    
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return False, "invalid_smiles", {}
    
    # Count features
    n_aromatic_rings = Descriptors.NumAromaticRings(mol)
    n_hba = Lipinski.NumHAcceptors(mol)  # H-bond acceptors
    n_hbd = Lipinski.NumHDonors(mol)  # H-bond donors
    
    # Count basic nitrogens (can interact with HIS185/ARG265)
    basic_n = 0
    for atom in mol.GetAtoms():
        if atom.GetSymbol() == 'N':
            # Check if nitrogen is basic (not in amide, not aromatic if possible)
            # Simple heuristic: primary/secondary/tertiary amines
            if atom.GetTotalNumHs() > 0 or atom.GetDegree() == 3:
                # Could be basic
                basic_n += 1
    
    # Count heteroatoms (not just hydrocarbons)
    n_hetero = sum(1 for atom in mol.GetAtoms() if atom.GetSymbol() not in ('C', 'H'))
    
    features = {
        "aromatic_rings": n_aromatic_rings,
        "hba": n_hba,
        "hbd": n_hbd,
        "basic_n": basic_n,
        "heteroatoms": n_hetero,
    }
    
    # Check requirements
    failures = []
    
    if n_aromatic_rings < 1:
        failures.append("no_aromatic_ring")
    
    if n_hba < 1:
        failures.append("no_hbond_acceptor")
    
    if n_hbd < 1 and basic_n < 1:
        failures.append("no_hbond_donor_or_basic_n")
    
    if n_hetero < 2:
        failures.append("too_few_heteroatoms")
    
    if len(failures) == 0:
        return True, "pharmacophore_match", features
    else:
        reason = "pharmacophore_fail:" + ",".join(failures)
        return False, reason, features


def check_pfdhod_pharmacophore(smiles: str) -> dict[str, any]:
    """
    Full PfDHODH pharmacophore check with detailed results.
    
    Returns dict with:
        - passes: bool
        - reason: str
        - features: dict of feature counts
        - score: float (0-100, LOCAL metric only)
    """
    passes, reason, features = check_pharmacophore(smiles)
    
    # Compute LOCAL pharmacophore score (0-100)
    # This is NOT an official GPU score
    score = 0.0
    if features:
        # Aromatic rings: up to 30 points (max 2 rings)
        score += min(features.get("aromatic_rings", 0) * 15, 30)
        
        # HBA: up to 25 points (max 3 acceptors)
        score += min(features.get("hba", 0) * 8, 25)
        
        # HBD or basic N: up to 25 points
        hbd_basic = features.get("hbd", 0) + features.get("basic_n", 0)
        score += min(hbd_basic * 8, 25)
        
        # Heteroatoms: up to 20 points (min 2 required, max 6 counted)
        hetero = max(0, features.get("heteroatoms", 0) - 1)  # -1 because 2 is minimum
        score += min(hetero * 4, 20)
    
    return {
        "passes": passes,
        "reason": reason,
        "features": features,
        "pharmacophore_score": score,
        "source": "local_pfdhod_pharmacophore_check",
    }


# PDB 5TBO information (DSM265 bound to PfDHODH)
# 3D docking is implemented in discovery/judgment/dock.py (AutoDock Vina wrapper)
# This module (pocket.py) provides 2D pharmacophore filtering only
PDB_INFO = {
    "pdb_id": "5TBO",
    "ligand": "DSM265",
    "key_residues": ["HIS185", "ARG265"],
    "description": "PfDHODH bound to DSM265 (triazolopyrimidine)",
    "note": "3D docking available in dock.py - this module is 2D SMARTS/Lipinski only",
}
