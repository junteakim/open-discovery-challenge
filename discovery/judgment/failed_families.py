"""Failed family fingerprint reject using known failed submissions."""

from __future__ import annotations

from discovery.chemistry.fingerprints import max_similarity, morgan_fp, tanimoto


# Known failed molecule families from REAL submissions.
# These are ACTUAL SMILES from /api/leaderboard with REAL official scores.
# Source: Official leaderboard 2026-08-20. DO NOT invent scores.
FAILED_SUBMISSIONS = {
    "ODC-5E9964": {
        "smiles": "COc1cc2[nH]cnc2cc1-c1ccc(S(=O)(=O)NCc2ccc(-c3cccc(C(F)(F)F)c3)cc2)cc1",
        "total": 41.397,
        "axes": {"selectivity": 1.69, "binding": 12.35, "activity": 18.23},
        "reason": "low_selectivity_random_hop",
    },
    "ODC-8F7407": {
        "smiles": "COc1c(-c2ccc(-c3ccccc3)cc2)c(-c2ccccc2CNC(=O)c2ccccc2)cc2cncnc12",
        "total": 19.082,
        "axes": {"selectivity": 0.0, "binding": 0.76, "activity": 12.28},
        "reason": "low_selectivity_random_hop",
    },
    "ODC-DA0285": {
        "smiles": "O=C(Nc1ccccc1-c1ncnc(-c2ccccc2NS(=O)(=O)c2ccccc2)n1)c1ccccc1",
        "total": 5.952,
        "axes": {"selectivity": 0.0, "binding": 0.35, "activity": 3.71},
        "reason": "low_selectivity_random_hop",
    },
    "ODC-2375B0": {
        "smiles": "O=C(NCc1ccccc1-c1cncnc1-c1ccccc1NS(=O)(=O)c1ccccc1)c1ccccc1",
        "total": 6.666,
        "axes": {"selectivity": 0.0, "binding": 0.07, "activity": 4.32},
        "reason": "low_selectivity_random_hop",
    },
    "ODC-77DF62": {
        "smiles": "O=S(=O)(Nc1ccccc1-c1cc2cc[nH]c2cc1-c1ccc(-c2ccccc2)cc1)c1ccccc1",
        "total": 13.135,
        "axes": {"selectivity": 0.2, "binding": 0.27, "activity": 8.15},
        "reason": "low_selectivity_random_hop",
    },
    "ODC-618680": {
        "smiles": "O=S(=O)(Nc1ccccc1-c1cc2ccoc2cc1-c1cccc(-c2ccccc2)c1)c1ccccc1",
        "total": 10.278,
        "axes": {"selectivity": 0.0, "binding": 0.49, "activity": 6.29},
        "reason": "low_selectivity_random_hop",
    },
    "ODC-85EC2C": {
        "smiles": "COc1ccc2cc(-c3ccccc3NC(=O)c3ccccc3)c(-c3ccc(-c4ccccc4)cc3)cc2n1",
        "total": 16.194,
        "axes": {"selectivity": 0.06, "binding": 0.16, "activity": 10.52},
        "reason": "low_selectivity_random_hop",
    },
}

# Extract just the SMILES for easy iteration
FAILED_SMILES = [entry["smiles"] for entry in FAILED_SUBMISSIONS.values()]


# Tanimoto threshold for "too similar to failed family"
FAILED_FAMILY_TANIMOTO_THRESHOLD = 0.60


def is_failed_family_analogue(smiles: str, threshold: float | None = None) -> tuple[bool, float, str]:
    """
    Check if a molecule is too similar to known failed submissions.
    
    Args:
        smiles: Candidate SMILES
        threshold: Tanimoto threshold (default 0.60)
    
    Returns:
        (is_analogue, max_similarity, reason)
        
    Examples:
        >>> is_failed_family_analogue("CCO")
        (False, 0.0, "")
        
        >>> # A close analogue would return:
        >>> # (True, 0.75, "similar_to_failed:benzimidazole_sulfonamide_CF3_5E9964:tanimoto=0.75")
    """
    if threshold is None:
        threshold = FAILED_FAMILY_TANIMOTO_THRESHOLD
    
    fp = morgan_fp(smiles)
    if fp is None:
        return False, 0.0, ""
    
    max_sim = 0.0
    closest_key = ""
    
    for key, entry in FAILED_SUBMISSIONS.items():
        failed_smiles = entry["smiles"]
        failed_fp = morgan_fp(failed_smiles)
        if failed_fp is not None:
            sim = tanimoto(fp, failed_fp)
            if sim > max_sim:
                max_sim = sim
                closest_key = key
    
    if max_sim >= threshold:
        return True, max_sim, f"similar_to_failed:{closest_key}:tanimoto={max_sim:.3f}"
    
    return False, max_sim, ""


def check_failed_family(smiles: str) -> dict[str, any]:
    """
    Check a molecule against known failed families.
    
    Returns dict with:
        - passed: bool
        - max_similarity: float
        - closest_failed: str (key from FAILED_SUBMISSIONS)
        - reason: str
    """
    is_analogue, max_sim, reason = is_failed_family_analogue(smiles)
    
    closest_key = ""
    if reason:
        # Extract key from reason string
        parts = reason.split(":")
        if len(parts) >= 2:
            closest_key = parts[1]
    
    return {
        "passed": not is_analogue,
        "max_similarity": max_sim,
        "closest_failed": closest_key,
        "reason": reason if reason else "no_failed_family_match",
    }
