"""Warhead-constrained molecule generator using RDKit CombineMols+AddBond.

Implements warhead-anchored growing using proper RDKit molecule combination.
Uses non-DSM warheads (pyrazole, aniline, phenol) from ReLink-PyB paper approach.
"""

from __future__ import annotations

import random
from typing import Iterator

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem, Descriptors, Crippen, rdMolDescriptors
except ImportError:  # pragma: no cover
    Chem = None
    AllChem = None
    Descriptors = None
    Crippen = None
    rdMolDescriptors = None

from discovery.chemistry.smiles import validate_structure
from discovery.gates.runner import GateRunner


# Non-DSM warheads for PfDHODH (ReLink-PyB paper used pyrazole and benzene)
# DSM265 uses triazolopyrimidine which we MUST avoid (novelty gate poison)
# These are SMARTS patterns for detection
WARHEAD_SMARTS = {
    "pyrazole": "c1c[nH]cn1",
    "pyrazole_alt": "c1c[nH]nn1",
    "aniline": "c1ccc(N)cc1",
    "phenol": "c1ccc(O)cc1",
}

# Core warhead structures with attachment points
# Format: (name, SMILES_with_dummy_atom, attachment_atom_idx)
WARHEAD_CORES = [
    ("pyrazole", "c1c[nH]cn1", 0),  # Attach at C position
    ("aniline", "Nc1ccccc1", 1),  # Attach at ipso carbon (next to N)
    ("phenol", "Oc1ccccc1", 1),  # Attach at ipso carbon (next to O)
]

# Linker/extension fragments with attachment points
# Format: (SMILES, attachment_idx_1, attachment_idx_2, has_hba)
# Prioritize fragments with H-bond acceptors for PfDHODH pharmacophore
LINKER_FRAGMENTS = [
    # H-bond acceptor linkers (preferred for HIS185/ARG265 interaction)
    ("c1ccncc1", 0, 3, True),  # Pyridine (N is HBA)
    ("CC(=O)N", 0, 2, True),  # Acetamide (C=O is HBA)
    ("CC(=O)", 0, 1, True),  # Carbonyl (HBA)
    ("CCN", 0, 2, True),  # Ethylamine (N is HBA/HBD)
    ("c1ccc(OC)cc1", 0, 4, True),  # Methoxyphenyl (O is HBA)
    ("CNC(=O)", 0, 2, True),  # N-methylamide (HBA)
    ("c1cc(N)ccc1", 0, 4, True),  # Aniline (N is HBD)
    
    # Simple aromatic (less preferred, no clear HBA)
    ("c1ccccc1", 0, 4, False),  # Phenyl
    ("c1ccc(Cl)cc1", 0, 4, False),  # Chlorophenyl
    
    # Short alkyl (discouraged - use sparingly)
    ("CC", 0, 1, False),  # Ethyl (only if needed)
    ("CCC", 0, 2, False),  # Propyl (only if needed)
]

# Terminal capping groups
TERMINAL_GROUPS = [
    ("C", 0),  # Methyl
    ("CC", 0),  # Ethyl
    ("C(C)C", 0),  # Isopropyl
    ("c1ccccc1", 0),  # Phenyl
    ("c1ccc(OC)cc1", 0),  # Methoxyphenyl
    ("c1ccc(C(F)(F)F)cc1", 0),  # Trifluoromethylphenyl
    ("C(=O)NCC", 0),  # Ethyl amide
]


def combine_mols_with_bond(mol1: Chem.Mol, mol2: Chem.Mol, atom1_idx: int, atom2_idx: int) -> Chem.Mol | None:
    """
    Combine two molecules by adding a single bond between specified atoms.
    
    Args:
        mol1, mol2: RDKit molecules
        atom1_idx: Atom index in mol1 to connect
        atom2_idx: Atom index in mol2 to connect (will be offset after combination)
    
    Returns:
        Combined molecule or None if failed
    """
    if Chem is None:
        return None
    
    try:
        # Combine molecules
        combo = Chem.CombineMols(mol1, mol2)
        editable = Chem.EditableMol(combo)
        
        # Atom indices after combination: mol2 atoms are offset by mol1.GetNumAtoms()
        offset_atom2_idx = mol1.GetNumAtoms() + atom2_idx
        
        # Add single bond
        editable.AddBond(atom1_idx, offset_atom2_idx, Chem.BondType.SINGLE)
        
        # Get result and sanitize
        result = editable.GetMol()
        Chem.SanitizeMol(result)
        
        return result
    except Exception:
        return None


def has_warhead(smiles: str) -> tuple[bool, list[str]]:
    """
    Check if a molecule contains one of the allowed warheads.
    
    Returns:
        (has_warhead, list_of_matching_warheads)
    """
    if Chem is None:
        return False, []
    
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return False, []
    
    matches = []
    for name, smarts in WARHEAD_SMARTS.items():
        pattern = Chem.MolFromSmarts(smarts)
        if pattern is not None and mol.HasSubstructMatch(pattern):
            matches.append(name)
    
    return len(matches) > 0, matches


def compute_drug_likeness(mol: Chem.Mol) -> dict[str, float]:
    """Compute simple drug-likeness metrics."""
    if Descriptors is None or Crippen is None:
        return {}
    
    return {
        "mw": Descriptors.MolWt(mol),
        "logp": Crippen.MolLogP(mol),
        "heavy_atoms": mol.GetNumHeavyAtoms(),
        "rotatable_bonds": Descriptors.NumRotatableBonds(mol),
    }


def is_drug_like(mol: Chem.Mol, mw_range: tuple[float, float] = (300, 550)) -> bool:
    """Check if molecule is roughly drug-like."""
    props = compute_drug_likeness(mol)
    if not props:
        return False
    
    mw = props.get("mw", 0)
    heavy = props.get("heavy_atoms", 0)
    logp = props.get("logp", 0)
    
    # Prefer MW 300-550, heavy≤45, reasonable logP
    return (
        mw_range[0] <= mw <= mw_range[1]
        and heavy <= 45
        and -2 <= logp <= 6
    )


class WarheadConstrainedGenerator:
    """
    Generate molecules with required warheads using RDKit CombineMols.
    
    This uses proper chemical combination, not string smashing.
    """
    
    def __init__(
        self,
        gate_runner: GateRunner | None = None,
        rng: random.Random | None = None,
        mw_range: tuple[float, float] = (300, 550),
    ):
        self.gate_runner = gate_runner or GateRunner()
        self.rng = rng or random.Random()
        self.mw_range = mw_range
    
    def build_molecule(self, n_extensions: int = 2) -> tuple[Chem.Mol | None, str]:
        """
        Build a molecule: warhead + linkers + terminal.
        
        Prefers linkers with H-bond acceptors for PfDHODH pharmacophore.
        
        Returns:
            (mol, warhead_name) or (None, "")
        """
        if Chem is None:
            return None, ""
        
        # Pick warhead
        warhead_name, warhead_smiles, warhead_attach_idx = self.rng.choice(WARHEAD_CORES)
        current_mol = Chem.MolFromSmiles(warhead_smiles)
        if current_mol is None:
            return None, ""
        
        current_attach_idx = warhead_attach_idx
        has_hba_linker = False
        
        # Add linker extensions - prefer at least one with HBA
        for i in range(n_extensions):
            # On first extension, prefer HBA linkers (80% chance)
            if i == 0 and self.rng.random() < 0.8:
                # Filter for HBA linkers
                hba_linkers = [l for l in LINKER_FRAGMENTS if len(l) > 3 and l[3]]
                if hba_linkers:
                    linker_data = self.rng.choice(hba_linkers)
                else:
                    linker_data = self.rng.choice(LINKER_FRAGMENTS)
            else:
                linker_data = self.rng.choice(LINKER_FRAGMENTS)
            
            linker_smiles = linker_data[0]
            link_idx1 = linker_data[1]
            link_idx2 = linker_data[2]
            if len(linker_data) > 3 and linker_data[3]:
                has_hba_linker = True
            
            linker_mol = Chem.MolFromSmiles(linker_smiles)
            if linker_mol is None:
                continue
            
            # Combine: attach current molecule's attach point to linker's first point
            combined = combine_mols_with_bond(current_mol, linker_mol, current_attach_idx, link_idx1)
            if combined is None:
                # Try different attachment
                combined = combine_mols_with_bond(current_mol, linker_mol, current_attach_idx, link_idx2)
            
            if combined is not None:
                current_mol = combined
                # New attachment point is where we attached the linker + offset
                current_attach_idx = current_mol.GetNumAtoms() - linker_mol.GetNumAtoms() + link_idx2
            else:
                break
        
        # Add terminal group
        terminal_smiles, terminal_idx = self.rng.choice(TERMINAL_GROUPS)
        terminal_mol = Chem.MolFromSmiles(terminal_smiles)
        if terminal_mol is not None:
            final_mol = combine_mols_with_bond(current_mol, terminal_mol, current_attach_idx, terminal_idx)
            if final_mol is not None:
                current_mol = final_mol
        
        return current_mol, warhead_name
    
    def generate_batch(
        self,
        n: int = 10,
    ) -> Iterator[tuple[str, str]]:
        """
        Generate up to n molecules with warheads.
        
        Yields:
            (canonical_smiles, warhead_type)
        """
        attempts = 0
        max_attempts = n * 100  # More attempts for proper molecule building
        produced = 0
        
        while produced < n and attempts < max_attempts:
            attempts += 1
            
            # Build molecule with 2-3 extensions
            n_extensions = self.rng.randint(2, 3)
            mol, warhead_name = self.build_molecule(n_extensions=n_extensions)
            
            if mol is None:
                continue
            
            # Check drug-likeness
            if not is_drug_like(mol, self.mw_range):
                continue
            
            # Check pharmacophore (reject pure hydrocarbon + ring only)
            # Import here to avoid circular dependency
            from discovery.judgment.pocket import check_pocket_pharmacophore
            pharma_result = check_pocket_pharmacophore(Chem.MolToSmiles(mol))
            pharma_pass = pharma_result["pass"]
            if not pharma_pass:
                # Skip molecules that fail basic pharmacophore
                continue
            
            # Get canonical SMILES
            try:
                smiles = Chem.MolToSmiles(mol)
                valid, canonical = validate_structure(smiles)
                if not valid or not canonical:
                    continue
            except Exception:
                continue
            
            # Verify warhead is present
            has_wh, _ = has_warhead(canonical)
            if not has_wh:
                continue
            
            # Check gates
            gate_result = self.gate_runner.check(canonical)
            if gate_result.passed and gate_result.canonical_smiles:
                self.gate_runner.register(gate_result.canonical_smiles)
                yield gate_result.canonical_smiles, warhead_name
                produced += 1


def generate_warhead_constrained_candidates(
    n: int = 10,
    gate_runner: GateRunner | None = None,
    seed: int | None = None,
    mw_range: tuple[float, float] = (300, 550),
) -> list[tuple[str, str]]:
    """
    Convenience function to generate a batch of warhead-constrained molecules.
    
    Args:
        n: Number of molecules to generate
        gate_runner: Optional GateRunner instance
        seed: Optional random seed
        mw_range: Target MW range (default 300-550)
    
    Returns:
        List of (smiles, warhead_type) tuples
    """
    rng = random.Random(seed) if seed is not None else random.Random()
    gen = WarheadConstrainedGenerator(gate_runner=gate_runner, rng=rng, mw_range=mw_range)
    return list(gen.generate_batch(n=n))
