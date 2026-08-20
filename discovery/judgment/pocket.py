"""2D pharmacophore checks for PfDHODH binding (LOCAL heuristic).

This is a 2D SMARTS/Lipinski rule-based check, NOT a 3D pocket analysis.
For 3D docking scores, see discovery.judgment.dock.

PfDHODH (PDB 5TBO) binding site:
- HIS185, ARG265 (H-bond donors/acceptors)
- Hydrophobic pocket
- Crystal ligands: DSM265, 78Z with pyrazole/triazolopyrimidine warheads

2D pharmacophore heuristics:
- Aromatic rings (π-stacking)
- H-bond acceptors (HBA) for HIS185/ARG265
- H-bond donors (HBD)
- Basic nitrogen (protonatable at physiological pH)
- Exclude pure alkyl chains (no heteroatoms)
"""
from __future__ import annotations

from rdkit import Chem
from rdkit.Chem import Lipinski, Descriptors


def check_pocket_pharmacophore(smiles: str) -> dict[str, any]:
    """
    2D SMARTS-based pharmacophore check for PfDHODH.
    
    Returns:
        {
            "pass": bool,
            "aromatic_rings": int,
            "hba": int,
            "hbd": int,
            "basic_n": int,
            "heteroatoms": int,
            "reason": str,
        }
    """
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {
            "pass": False,
            "aromatic_rings": 0,
            "hba": 0,
            "hbd": 0,
            "basic_n": 0,
            "heteroatoms": 0,
            "reason": "unparsed",
        }
    
    aromatic_rings = Lipinski.NumAromaticRings(mol)
    hba = Lipinski.NumHAcceptors(mol)
    hbd = Lipinski.NumHDonors(mol)
    
    # Count basic nitrogens (pyridine, amine, etc.)
    basic_n_smarts = Chem.MolFromSmarts("[nH,NH2,NH1,n]")
    basic_n = len(mol.GetSubstructMatches(basic_n_smarts)) if basic_n_smarts else 0
    
    # Heteroatoms (N, O, S, etc.)
    heteroatoms = sum(1 for atom in mol.GetAtoms() if atom.GetAtomicNum() not in (1, 6))
    
    # Fail if pure hydrocarbon (no heteroatoms)
    if heteroatoms == 0:
        return {
            "pass": False,
            "aromatic_rings": aromatic_rings,
            "hba": hba,
            "hbd": hbd,
            "basic_n": basic_n,
            "heteroatoms": heteroatoms,
            "reason": "pure_hydrocarbon_no_hbond",
        }
    
    # Require at least 1 aromatic ring (warhead or terminal group)
    if aromatic_rings < 1:
        return {
            "pass": False,
            "aromatic_rings": aromatic_rings,
            "hba": hba,
            "hbd": hbd,
            "basic_n": basic_n,
            "heteroatoms": heteroatoms,
            "reason": "no_aromatic_ring",
        }
    
    # Require at least 1 HBA for HIS185/ARG265 interaction
    if hba < 1:
        return {
            "pass": False,
            "aromatic_rings": aromatic_rings,
            "hba": hba,
            "hbd": hbd,
            "basic_n": basic_n,
            "heteroatoms": heteroatoms,
            "reason": "no_hba_for_his185_arg265",
        }
    
    # Pass: has aromatic ring(s), HBA, and heteroatoms
    return {
        "pass": True,
        "aromatic_rings": aromatic_rings,
        "hba": hba,
        "hbd": hbd,
        "basic_n": basic_n,
        "heteroatoms": heteroatoms,
        "reason": "pharmacophore_ok",
    }
