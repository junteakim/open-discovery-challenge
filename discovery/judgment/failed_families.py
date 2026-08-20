"""Failed family fingerprint reject using known failed submissions."""

from __future__ import annotations

from discovery.chemistry.fingerprints import max_similarity, morgan_fp, tanimoto


# Known failed molecule families from previous submissions.
# These are actual SMILES from failed submissions (scores 6-41, sel≈0).
# DO NOT invent scores or InChIKeys. These are documented historical failures.
FAILED_SUBMISSIONS = {
    "benzimidazole_sulfonamide_CF3_5E9964": {
        "smiles": "c1ccc2[nH]c(S(=O)(=O)NCC)nc2c1c1ccc(C(F)(F)F)cc1",
        "family": "benzimidazole_sulfonamide",
        "core": "benzimidazole",
        "score_range": "6-20",
        "selectivity_estimate": 0.0,
        "reason": "random_heterocycle_without_pharmacophore",
    },
    "quinazoline_8F7407": {
        "smiles": "c1ccc2c(c1)nc(NC(=O)NCCC)nc2c1ccc(OC)cc1",
        "family": "quinazoline_urea",
        "core": "quinazoline",
        "score_range": "15-25",
        "selectivity_estimate": 0.0,
        "reason": "random_heterocycle_without_pharmacophore",
    },
    "triazine_DA0285": {
        "smiles": "c1nc(Nc2ccc(OC)cc2)nc(c3ccc(C)cn3)n1CC(=O)",
        "family": "triazine_aniline",
        "core": "triazine",
        "score_range": "20-30",
        "selectivity_estimate": 0.0,
        "reason": "random_heterocycle_without_pharmacophore",
    },
    "pyrimidine_2375B0": {
        "smiles": "c1nc(CCC)nc(c2ccc(OC)cc2)c1S(=O)(=O)NCC",
        "family": "pyrimidine_sulfonamide",
        "core": "pyrimidine",
        "score_range": "30-41",
        "selectivity_estimate": 0.0,
        "reason": "random_heterocycle_without_pharmacophore",
    },
    "indole_77DF62": {
        "smiles": "c1ccc2[nH]c(C(=O)NCCC)cc2c1c1ccc(OC)c(c1)c1ccccc1",
        "family": "indole_carboxamide",
        "core": "indole",
        "score_range": "25-35",
        "selectivity_estimate": 0.0,
        "reason": "random_heterocycle_without_pharmacophore",
    },
    "benzofuran_618680": {
        "smiles": "c1ccc2oc(C(=O)NCCc3ccccc3)cc2c1c1ccc(OC)cc1",
        "family": "benzofuran_amide",
        "core": "benzofuran",
        "score_range": "18-28",
        "selectivity_estimate": 0.0,
        "reason": "random_heterocycle_without_pharmacophore",
    },
    "quinoline_85EC2C": {
        "smiles": "c1ccc2c(c1)ccc(C(=O)NCCOC)n2c1ccc(C(F)(F)F)cc1",
        "family": "quinoline_amide",
        "core": "quinoline",
        "score_range": "12-22",
        "selectivity_estimate": 0.0,
        "reason": "random_heterocycle_without_pharmacophore",
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
