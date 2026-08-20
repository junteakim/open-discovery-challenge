"""LOCAL AutoDock Vina against PfDHODH (5TBO) and HsDHODH (4IGH).

Not an official GPU score. Never invent kcal.

Pf box: 78Z / DSM421 centroid in 5TBO (23.498, -17.282, -15.054), 24 Å.
Hs box: 1EA centroid in 4IGH (-7.060, 34.707, -2.373), 24 Å.

local_sel_kcal = hs_kcal - pf_kcal
  more positive = prefers Pf (Hs weaker / Pf stronger).
This is NOT official selectivity.
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
SIZE = 24.0
MIN_LOCAL_SEL_KCAL = 2.0

TARGETS = {
    "pf": {
        "receptor": Path(os.environ.get("ODC_RECEPTOR_PF", os.environ.get("ODC_RECEPTOR", "/workspace/odc-dock/5tbo_receptor.pdbqt"))),
        "center": (23.498, -17.282, -15.054),
        "pdb": "5TBO",
        "source": "local_vina_5tbo",
    },
    "hs": {
        "receptor": Path(os.environ.get("ODC_RECEPTOR_HS", "/workspace/odc-dock/4igh_receptor.pdbqt")),
        "center": (-7.060, 34.707, -2.373),
        "pdb": "4IGH",
        "source": "local_vina_4igh",
    },
}

# Back-compat names
RECEPTOR = TARGETS["pf"]["receptor"]
CENTER = TARGETS["pf"]["center"]


def vina_available(target: str = "pf") -> bool:
    spec = TARGETS.get(target)
    if spec is None:
        return False
    rec = spec["receptor"]
    return VINA.is_file() and os.access(VINA, os.X_OK) and rec.is_file()


def dual_vina_available() -> bool:
    return vina_available("pf") and vina_available("hs")


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
    setups = prep.prepare(mol)
    setup = setups[0] if isinstance(setups, list) else (setups or prep.setup)
    if isinstance(setup, list):
        setup = setup[0]
    pdbqt, ok, err = PDBQTWriterLegacy.write_string(setup)
    if not ok:
        return None, f"pdbqt_failed:{err}"
    return pdbqt, "ok"


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


def _run_vina(pdbqt: str, target: str, exhaustiveness: int, num_modes: int, cpu: int) -> dict:
    spec = TARGETS[target]
    base = {
        "status": "unavailable",
        "kcal": None,
        "poses": [],
        "source": spec["source"],
        "receptor": spec["pdb"],
        "vina": None,
        "target": target,
    }
    if not vina_available(target):
        base["reason"] = f"vina_or_receptor_missing:{target}"
        return base
    rec = spec["receptor"]
    cx, cy, cz = spec["center"]
    with tempfile.TemporaryDirectory(prefix="odc-vina-") as td:
        lig = Path(td) / "lig.pdbqt"
        out = Path(td) / "out.pdbqt"
        lig.write_text(pdbqt)
        cmd = [
            str(VINA),
            "--receptor", str(rec),
            "--ligand", str(lig),
            "--center_x", str(cx),
            "--center_y", str(cy),
            "--center_z", str(cz),
            "--size_x", str(SIZE),
            "--size_y", str(SIZE),
            "--size_z", str(SIZE),
            "--exhaustiveness", str(exhaustiveness),
            "--num_modes", str(num_modes),
            "--cpu", str(cpu),
            "--out", str(out),
        ]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=600, check=False)
        except subprocess.TimeoutExpired:
            base["status"] = "failed"
            base["reason"] = "vina_timeout"
            return base
        poses = _parse_vina_table(proc.stdout or "")
        if proc.returncode != 0 or not poses:
            base["status"] = "failed"
            base["reason"] = f"vina_exit_{proc.returncode}"
            base["log_tail"] = ((proc.stdout or "") + "\n" + (proc.stderr or ""))[-800:]
            return base
        base["status"] = "ok"
        base["kcal"] = poses[0]["kcal"]
        base["poses"] = poses
        base["vina"] = "1.2.5"
        return base


def dock_smiles(
    smiles: str,
    target: str = "pf",
    exhaustiveness: int = 8,
    num_modes: int = 5,
    cpu: int = 2,
    pdbqt: str | None = None,
) -> dict:
    """Dock one SMILES to one target. LOCAL vina kcal only."""
    if target not in TARGETS:
        return {"smiles": smiles, "status": "failed", "kcal": None, "reason": f"unknown_target:{target}", "poses": []}
    if pdbqt is None:
        pdbqt, reason = _smiles_to_pdbqt(smiles)
        if pdbqt is None:
            return {
                "smiles": smiles,
                "status": "failed",
                "kcal": None,
                "poses": [],
                "reason": reason,
                "source": TARGETS[target]["source"],
                "receptor": TARGETS[target]["pdb"],
                "target": target,
            }
    result = _run_vina(pdbqt, target, exhaustiveness, num_modes, cpu)
    result["smiles"] = smiles
    return result


def dock_selectivity(
    smiles: str,
    exhaustiveness: int = 8,
    num_modes: int = 5,
    cpu: int = 2,
) -> dict:
    """Dock the same 3D ligand to Pf then Hs. LOCAL gap, not official sel."""
    empty = {
        "smiles": smiles,
        "status": "unavailable",
        "pf": None,
        "hs": None,
        "pf_kcal": None,
        "hs_kcal": None,
        "local_sel_kcal": None,
        "source": "local_vina_pf_hs",
    }
    if not dual_vina_available():
        empty["reason"] = "pf_or_hs_receptor_missing"
        return empty
    pdbqt, reason = _smiles_to_pdbqt(smiles)
    if pdbqt is None:
        empty["status"] = "failed"
        empty["reason"] = reason
        return empty
    pf = _run_vina(pdbqt, "pf", exhaustiveness, num_modes, cpu)
    hs = _run_vina(pdbqt, "hs", exhaustiveness, num_modes, cpu)
    pf["smiles"] = smiles
    hs["smiles"] = smiles
    gap = None
    status = "failed"
    if pf.get("status") == "ok" and hs.get("status") == "ok":
        gap = float(hs["kcal"]) - float(pf["kcal"])
        status = "ok"
    elif pf.get("status") != "ok":
        status = f"pf_{pf.get('status')}"
    else:
        status = f"hs_{hs.get('status')}"
    return {
        "smiles": smiles,
        "status": status,
        "pf": pf,
        "hs": hs,
        "pf_kcal": pf.get("kcal"),
        "hs_kcal": hs.get("kcal"),
        "local_sel_kcal": gap,
        "source": "local_vina_pf_hs",
        "reason": None if status == "ok" else (pf.get("reason") or hs.get("reason")),
    }


def dock_molecule(smiles: str) -> dict:
    """Alias: Pf-only dock. LOCAL vina."""
    return dock_smiles(smiles, target="pf")
