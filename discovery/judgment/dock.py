"""LOCAL AutoDock Vina docking against PfDHODH (PDB 5TBO). Not an official GPU score.

Requires:
  vina binary (default /workspace/bin/vina)
  receptor PDBQT (default /workspace/odc-dock/5tbo_receptor.pdbqt)
  meeko + rdkit to write ligand PDBQT

Box is the 78Z / DSM421 centroid in 5TBO:
  center (23.50, -17.28, -15.05), size 24 Å cube.

Never invent kcal. If vina is missing, status=unavailable.
"""
from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

try:
    from rdkit import Chem
    from rdkit.Chem import AllChem
except ImportError:  # pragma: no cover
    Chem = None
    AllChem = None

VINA = Path(os.environ.get("ODC_VINA", "/workspace/bin/vina"))
RECEPTOR = Path(os.environ.get("ODC_RECEPTOR", "/workspace/odc-dock/5tbo_receptor.pdbqt"))
CENTER = (23.498, -17.282, -15.054)
SIZE = 24.0


def vina_available() -> bool:
    return VINA.is_file() and os.access(VINA, os.X_OK) and RECEPTOR.is_file()


def _smiles_to_pdbqt(smiles: str) -> tuple[str | None, str]:
    if Chem is None:
        return None, "rdkit_missing"
    try:
        from meeko import MoleculePreparation, PDBQTWriterLegacy
    except ImportError:
        return None, "meeko_missing"
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None, "unparsed"
    mol = Chem.AddHs(mol)
    params = AllChem.ETKDGv3()
    params.randomSeed = 42
    if AllChem.EmbedMolecule(mol, params) != 0:
        if AllChem.EmbedMolecule(mol, AllChem.ETKDG()) != 0:
            return None, "embed_failed"
    try:
        AllChem.UFFOptimizeMolecule(mol, maxIters=200)
    except Exception:
        pass
    prep = MoleculePreparation()
    prep.prepare(mol)
    setup = prep.setup
    if isinstance(setup, list):
        setup = setup[0]
    pdbqt, ok, err = PDBQTWriterLegacy.write_string(setup)
    if not ok:
        return None, f"pdbqt_failed:{err}"
    return pdbqt, "ok"


def dock_smiles(
    smiles: str,
    exhaustiveness: int = 8,
    num_modes: int = 5,
    cpu: int = 2,
) -> dict:
    """Dock one SMILES. LOCAL vina kcal only. Not official GPU."""
    base = {
        "smiles": smiles,
        "status": "unavailable",
        "kcal": None,
        "poses": [],
        "source": "local_vina_5tbo",
        "receptor": "5TBO",
        "vina": None,
    }
    if not vina_available():
        base["reason"] = "vina_or_receptor_missing"
        return base
    pdbqt, reason = _smiles_to_pdbqt(smiles)
    if pdbqt is None:
        base["status"] = "failed"
        base["reason"] = reason
        return base
    with tempfile.TemporaryDirectory(prefix="odc-vina-") as td:
        lig = Path(td) / "lig.pdbqt"
        out = Path(td) / "out.pdbqt"
        lig.write_text(pdbqt)
        cmd = [
            str(VINA),
            "--receptor", str(RECEPTOR),
            "--ligand", str(lig),
            "--center_x", str(CENTER[0]),
            "--center_y", str(CENTER[1]),
            "--center_z", str(CENTER[2]),
            "--size_x", str(SIZE),
            "--size_y", str(SIZE),
            "--size_z", str(SIZE),
            "--exhaustiveness", str(exhaustiveness),
            "--num_modes", str(num_modes),
            "--cpu", str(cpu),
            "--out", str(out),
        ]
        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True, timeout=600, check=False
            )
        except subprocess.TimeoutExpired:
            base["status"] = "failed"
            base["reason"] = "vina_timeout"
            return base
        log = (proc.stdout or "") + "\n" + (proc.stderr or "")
        poses = _parse_vina_table(proc.stdout or "")
        if proc.returncode != 0 or not poses:
            base["status"] = "failed"
            base["reason"] = f"vina_exit_{proc.returncode}"
            base["log_tail"] = log[-800:]
            return base
        base["status"] = "ok"
        base["kcal"] = poses[0]["kcal"]
        base["poses"] = poses
        base["vina"] = "1.2.5"
        return base


def _parse_vina_table(stdout: str) -> list[dict]:
    poses = []
    in_table = False
    for line in stdout.splitlines():
        if "mode |" in line or line.strip().startswith("-----+"):
            in_table = True
            continue
        if not in_table:
            continue
        parts = line.split()
        if len(parts) >= 3:
            try:
                poses.append({
                    "mode": int(parts[0]),
                    "kcal": float(parts[1]),
                    "rmsd_lb": float(parts[2]),
                    "rmsd_ub": float(parts[3]) if len(parts) > 3 else None,
                })
            except ValueError:
                continue
    return poses


def dock_molecule(smiles: str) -> dict:
    """Alias for dock_smiles. LOCAL vina only."""
    return dock_smiles(smiles)
