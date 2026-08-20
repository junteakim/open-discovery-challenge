"""AutoDock Vina docking wrapper for PfDHODH (LOCAL scores only).

Uses PDB 5TBO (DSM265 binding site) with meeko-prepared receptor.
Returns LOCAL kcal/mol scores - NOT official GPU scores.

Box parameters (78Z/DSM421 centroid in 5TBO):
- Center: (23.498, -17.282, -15.054)
- Size: 24 Å cubic

Environment variables:
- ODC_VINA: path to vina binary (default: /workspace/bin/vina)
- ODC_RECEPTOR: path to receptor PDBQT (required for docking)

If vina or receptor missing, returns status=unavailable (does NOT fake kcal).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem
except ImportError:  # pragma: no cover
    Chem = None
    AllChem = None


# Vina box parameters for PfDHODH 5TBO
VINA_BOX = {
    "center_x": 23.498,
    "center_y": -17.282,
    "center_z": -15.054,
    "size_x": 24,
    "size_y": 24,
    "size_z": 24,
}


def check_vina_available() -> tuple[bool, Path | None, str]:
    """
    Check if Vina binary and receptor are available.
    
    Returns:
        (available, vina_path, reason)
    """
    # Check for vina binary
    vina_path = os.environ.get("ODC_VINA")
    if vina_path and Path(vina_path).exists():
        vina_bin = Path(vina_path)
    else:
        # Try default location
        default_vina = Path("/workspace/bin/vina")
        if default_vina.exists():
            vina_bin = default_vina
        else:
            # Try system PATH
            which_vina = shutil.which("vina")
            if which_vina:
                vina_bin = Path(which_vina)
            else:
                return False, None, "vina_binary_not_found"
    
    # Check for receptor
    receptor_path = os.environ.get("ODC_RECEPTOR")
    if not receptor_path or not Path(receptor_path).exists():
        return False, None, "receptor_pdbqt_not_found_set_ODC_RECEPTOR"
    
    return True, vina_bin, "available"


def smiles_to_pdbqt(smiles: str, output_path: Path) -> bool:
    """
    Convert SMILES to ligand PDBQT using RDKit + meeko.
    
    Args:
        smiles: Input SMILES
        output_path: Where to write PDBQT
    
    Returns:
        Success bool
    """
    if Chem is None:
        return False
    
    try:
        # Parse SMILES
        mol = Chem.MolFromSmiles(smiles)
        if mol is None:
            return False
        
        # Add hydrogens
        mol = Chem.AddHs(mol)
        
        # Generate 3D conformation (ETKDG)
        params = AllChem.ETKDGv3()
        params.randomSeed = 42
        result = AllChem.EmbedMolecule(mol, params)
        if result != 0:
            # Try without ETKDG
            result = AllChem.EmbedMolecule(mol)
            if result != 0:
                return False
        
        # Optimize with UFF
        AllChem.UFFOptimizeMolecule(mol)
        
        # Convert to PDBQT using meeko
        try:
            from meeko import MoleculePreparation, PDBQTWriterLegacy
        except ImportError:
            # If meeko not available, try RDKit's PDB writer + manual PDBQT conversion
            # (less reliable, but better than nothing)
            return False
        
        # Prepare molecule
        preparator = MoleculePreparation()
        preparator.prepare(mol)
        
        # Write PDBQT
        writer = PDBQTWriterLegacy()
        pdbqt_string = writer.write_string(preparator.setup)
        
        output_path.write_text(pdbqt_string)
        return True
    
    except Exception:
        return False


def run_vina_docking(
    ligand_pdbqt: Path,
    receptor_pdbqt: Path,
    vina_bin: Path,
    output_dir: Path,
) -> dict[str, any]:
    """
    Run AutoDock Vina docking.
    
    Returns:
        Dict with status, kcal, poses, etc.
    """
    output_pdbqt = output_dir / "output.pdbqt"
    log_file = output_dir / "vina.log"
    
    # Build vina command
    cmd = [
        str(vina_bin),
        "--receptor", str(receptor_pdbqt),
        "--ligand", str(ligand_pdbqt),
        "--out", str(output_pdbqt),
        "--center_x", str(VINA_BOX["center_x"]),
        "--center_y", str(VINA_BOX["center_y"]),
        "--center_z", str(VINA_BOX["center_z"]),
        "--size_x", str(VINA_BOX["size_x"]),
        "--size_y", str(VINA_BOX["size_y"]),
        "--size_z", str(VINA_BOX["size_z"]),
        "--exhaustiveness", "8",
        "--cpu", "1",
    ]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )
        
        log_file.write_text(result.stdout + "\n" + result.stderr)
        
        if result.returncode != 0:
            return {
                "status": "vina_failed",
                "kcal": None,
                "reason": f"vina_exit_code_{result.returncode}",
            }
        
        # Parse output
        poses = parse_vina_output(result.stdout)
        if not poses:
            return {
                "status": "vina_no_poses",
                "kcal": None,
                "reason": "no_poses_in_output",
            }
        
        # Best pose (first one)
        best_kcal = poses[0]["affinity"]
        
        return {
            "status": "success",
            "kcal": best_kcal,
            "poses": poses,
            "log": str(log_file),
        }
    
    except subprocess.TimeoutExpired:
        return {
            "status": "vina_timeout",
            "kcal": None,
            "reason": "docking_timeout_300s",
        }
    except Exception as e:
        return {
            "status": "vina_error",
            "kcal": None,
            "reason": str(e),
        }


def parse_vina_output(vina_stdout: str) -> list[dict]:
    """
    Parse Vina output table to extract poses and affinities.
    
    Returns:
        List of dicts with mode, affinity, rmsd_lb, rmsd_ub
    """
    poses = []
    in_table = False
    
    for line in vina_stdout.split("\n"):
        line = line.strip()
        
        # Look for table header
        if "mode |" in line and "affinity" in line:
            in_table = True
            continue
        
        # Parse table rows
        if in_table and line and not line.startswith("-"):
            parts = line.split()
            if len(parts) >= 4:
                try:
                    mode = int(parts[0])
                    affinity = float(parts[1])
                    rmsd_lb = float(parts[2])
                    rmsd_ub = float(parts[3])
                    
                    poses.append({
                        "mode": mode,
                        "affinity": affinity,
                        "rmsd_lb": rmsd_lb,
                        "rmsd_ub": rmsd_ub,
                    })
                except (ValueError, IndexError):
                    continue
        
        # End of table
        if in_table and line.startswith("Writing output"):
            break
    
    return poses


def dock_molecule(smiles: str) -> dict[str, any]:
    """
    Dock molecule into PfDHODH 5TBO pocket.
    
    Returns LOCAL docking score (NOT official GPU score).
    If vina/receptor missing, returns status=unavailable (does NOT fake kcal).
    
    Args:
        smiles: SMILES to dock
    
    Returns:
        Dict with:
            - status: str (success, unavailable, failed, etc.)
            - kcal: float | None (affinity in kcal/mol, more negative = better)
            - poses: list | None (all poses if available)
            - receptor: str (5TBO)
            - source: str (always "local_vina_5tbo")
    """
    # Check availability
    available, vina_bin, reason = check_vina_available()
    
    if not available:
        return {
            "status": "unavailable",
            "kcal": None,
            "reason": reason,
            "receptor": "5TBO",
            "source": "local_vina_5tbo",
        }
    
    receptor_path = Path(os.environ["ODC_RECEPTOR"])
    
    # Create temp directory for docking
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        ligand_pdbqt = tmp_path / "ligand.pdbqt"
        
        # Convert SMILES to PDBQT
        success = smiles_to_pdbqt(smiles, ligand_pdbqt)
        if not success:
            return {
                "status": "ligand_prep_failed",
                "kcal": None,
                "reason": "smiles_to_pdbqt_failed",
                "receptor": "5TBO",
                "source": "local_vina_5tbo",
            }
        
        # Run docking
        dock_result = run_vina_docking(
            ligand_pdbqt,
            receptor_path,
            vina_bin,
            tmp_path,
        )
        
        # Add metadata
        dock_result["receptor"] = "5TBO"
        dock_result["source"] = "local_vina_5tbo"
        
        return dock_result


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
