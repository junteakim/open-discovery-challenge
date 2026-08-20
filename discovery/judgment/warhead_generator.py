"""Warhead-constrained molecule generator.

Implements a simple warhead-anchored growing strategy using RDKit.
Uses non-DSM warheads (pyrazole, benzene) from ReLink-PyB paper approach.

This is NOT using the full REINVENT/LinkINVENT framework, but a simpler
RDKit CombineMols + AddBond approach for linker growing.
"""

from __future__ import annotations

import random
from typing import Iterator

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem
except ImportError:  # pragma: no cover
    Chem = None
    AllChem = None

from discovery.chemistry.smiles import validate_structure
from discovery.gates.runner import GateRunner


# Non-DSM warheads for PfDHODH (ReLink-PyB paper used pyrazole and benzene)
# DSM265 uses triazolopyrimidine which we MUST avoid (novelty gate poison)
WARHEAD_SMARTS = {
    "pyrazole": "c1cc[nH]n1",  # Pyrazole ring
    "pyrazole_NH": "c1c[nH]nc1",  # Alternative tautomer
    "benzene_NH2": "c1ccc(N)cc1",  # Aniline warhead
    "phenol": "c1ccc(O)cc1",  # Phenol warhead
}

# Linker fragments to grow from warhead
LINKER_FRAGMENTS = [
    "CC",  # ethyl
    "CCC",  # propyl
    "CCCC",  # butyl
    "CCO",  # ethoxy
    "CCOC",  # propoxy
    "CC(=O)",  # acetyl
    "CC(=O)N",  # acetamide
    "CS",  # thiomethyl
    "CCN",  # ethylamine
    "c1ccccc1",  # phenyl
    "c1ccc(OC)cc1",  # methoxyphenyl
    "c1ccc(Cl)cc1",  # chlorophenyl
    "c1ccc(F)cc1",  # fluorophenyl
    "c1ccncc1",  # pyridine
    "c1cccnc1",  # pyridine (alt)
]

# Terminal groups to cap grown molecules
TERMINAL_GROUPS = [
    "C",  # methyl
    "CC",  # ethyl
    "C(C)C",  # isopropyl
    "c1ccccc1",  # phenyl
    "c1ccc(OC)cc1",  # methoxyphenyl
    "c1ccc(C(F)(F)F)cc1",  # trifluoromethylphenyl
    "C(=O)NCC",  # ethyl amide
    "C(=O)NCCC",  # propyl amide
    "S(=O)(=O)NCC",  # ethyl sulfonamide
]


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


def simple_warhead_molecule(warhead: str, linkers: list[str], terminal: str) -> str | None:
    """
    Build a simple molecule: warhead-linker(s)-terminal.
    
    This is a simplified approach using SMILES concatenation with explicit bonds.
    Returns canonical SMILES or None if invalid.
    """
    if Chem is None:
        return None
    
    # Start with warhead
    smiles = warhead
    
    # Add linkers
    for linker in linkers:
        smiles = f"{smiles}{linker}"
    
    # Add terminal
    smiles = f"{smiles}{terminal}"
    
    # Validate and canonicalize
    valid, canonical = validate_structure(smiles)
    if valid and canonical:
        return canonical
    
    # Try with explicit single bonds
    smiles_with_bonds = warhead
    for linker in linkers:
        smiles_with_bonds = f"{smiles_with_bonds}-{linker}"
    smiles_with_bonds = f"{smiles_with_bonds}-{terminal}"
    
    valid, canonical = validate_structure(smiles_with_bonds)
    if valid and canonical:
        return canonical
    
    return None


class WarheadConstrainedGenerator:
    """
    Generate molecules with required warheads.
    
    This is a simple implementation that combines warheads with linkers
    and terminal groups, then filters through gates.
    """
    
    def __init__(
        self,
        gate_runner: GateRunner | None = None,
        rng: random.Random | None = None,
    ):
        self.gate_runner = gate_runner or GateRunner()
        self.rng = rng or random.Random()
        self._warheads = list(WARHEAD_SMARTS.values())
    
    def generate_batch(
        self,
        n: int = 10,
        max_linkers: int = 3,
    ) -> Iterator[tuple[str, str]]:
        """
        Generate up to n molecules with warheads.
        
        Yields:
            (canonical_smiles, warhead_type)
        """
        attempts = 0
        max_attempts = n * 50
        produced = 0
        
        while produced < n and attempts < max_attempts:
            attempts += 1
            
            # Pick warhead
            warhead = self.rng.choice(self._warheads)
            warhead_name = [k for k, v in WARHEAD_SMARTS.items() if v == warhead][0]
            
            # Pick 1-3 linkers
            n_linkers = self.rng.randint(1, max_linkers)
            linkers = [self.rng.choice(LINKER_FRAGMENTS) for _ in range(n_linkers)]
            
            # Pick terminal
            terminal = self.rng.choice(TERMINAL_GROUPS)
            
            # Build molecule
            smiles = simple_warhead_molecule(warhead, linkers, terminal)
            if smiles is None:
                continue
            
            # Check gates
            gate_result = self.gate_runner.check(smiles)
            if gate_result.passed and gate_result.canonical_smiles:
                # Verify warhead is still present after canonicalization
                has_wh, _ = has_warhead(gate_result.canonical_smiles)
                if has_wh:
                    self.gate_runner.register(gate_result.canonical_smiles)
                    yield gate_result.canonical_smiles, warhead_name
                    produced += 1


def generate_warhead_constrained_candidates(
    n: int = 10,
    gate_runner: GateRunner | None = None,
    seed: int | None = None,
) -> list[tuple[str, str]]:
    """
    Convenience function to generate a batch of warhead-constrained molecules.
    
    Args:
        n: Number of molecules to generate
        gate_runner: Optional GateRunner instance
        seed: Optional random seed
    
    Returns:
        List of (smiles, warhead_type) tuples
    """
    rng = random.Random(seed) if seed is not None else random.Random()
    gen = WarheadConstrainedGenerator(gate_runner=gate_runner, rng=rng)
    return list(gen.generate_batch(n=n))
