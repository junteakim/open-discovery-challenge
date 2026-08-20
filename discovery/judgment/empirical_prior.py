"""Empirical prior from official leaderboard conditionals.

These are documented empirical facts from the official leaderboard API
(computed 2026-08-20 from /api/leaderboard?season=1, n=2415 scored).

DO NOT treat these as official GPU scores. These are LOCAL priors only.
DO NOT update these with invented numbers. These are historical statistics.
"""

from __future__ import annotations

from dataclasses import dataclass

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors
except ImportError:  # pragma: no cover
    Chem = None
    Descriptors = None


# Official leaderboard conditionals (2026-08-20, n=2415)
# Source: /api/leaderboard?season=1
# These are empirical facts, not predictions.
OFFICIAL_CONDITIONALS = {
    # P(total≥60 | selectivity < 3) = 0/1169 = 0.0
    "low_selectivity_high_score": {
        "condition": "selectivity < 3 AND total >= 60",
        "count": 0,
        "total_matching_condition": 1169,
        "probability": 0.0,
        "source": "official_leaderboard_2026_08_20",
    },
    # P(total≥60 | MW 500-550 AND sel < 3) = 0/64 = 0.0
    "mw_500_550_low_sel_high_score": {
        "condition": "MW 500-550 AND selectivity < 3 AND total >= 60",
        "count": 0,
        "total_matching_condition": 64,
        "probability": 0.0,
        "source": "official_leaderboard_2026_08_20",
    },
    # P(total≥60 | MW 500-550 AND sel ≥ 10) = 116/118 ≈ 0.983
    "mw_500_550_high_sel_high_score": {
        "condition": "MW 500-550 AND selectivity >= 10 AND total >= 60",
        "count": 116,
        "total_matching_condition": 118,
        "probability": 0.983,
        "source": "official_leaderboard_2026_08_20",
    },
}

# MW band statistics from leaderboard (same as discovery/scoring/prior.py)
MW_BAND_STATS = {
    "150-200": {"n": 8, "median": 2.1, "p10": 1.7, "max": 2.5, "gt60": 0},
    "200-250": {"n": 52, "median": 2.8, "p10": 1.9, "max": 16.8, "gt60": 0},
    "250-300": {"n": 100, "median": 7.3, "p10": 3.4, "max": 41.4, "gt60": 0},
    "300-350": {"n": 368, "median": 18.0, "p10": 5.3, "max": 71.5, "gt60": 5},
    "350-400": {"n": 648, "median": 36.2, "p10": 11.6, "max": 69.6, "gt60": 45},
    "400-450": {"n": 476, "median": 44.8, "p10": 16.6, "max": 73.8, "gt60": 71},
    "450-500": {"n": 304, "median": 42.6, "p10": 18.2, "max": 79.6, "gt60": 64},
    "500-550": {"n": 165, "median": 67.6, "p10": 25.7, "max": 84.6, "gt60": 103},
}


@dataclass
class EmpiricalPrior:
    """Local empirical prior result (NOT an official GPU score)."""

    smiles: str
    mw: float
    mw_band: str
    expected_p_ge_60: float  # Local expected P(total≥60) given features
    reason: str
    matching_conditionals: list[str]  # Which official conditionals apply
    source: str = "empirical_prior_from_official_leaderboard"


def compute_mw(smiles: str) -> float | None:
    """Return molecular weight or None if structure is invalid."""
    if Chem is None:
        return None
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    return Descriptors.MolWt(mol)


def get_mw_band(mw: float) -> str:
    """Classify MW into historical band."""
    if mw < 150:
        return "<150"
    elif mw < 200:
        return "150-200"
    elif mw < 250:
        return "200-250"
    elif mw < 300:
        return "250-300"
    elif mw < 350:
        return "300-350"
    elif mw < 400:
        return "350-400"
    elif mw < 450:
        return "400-450"
    elif mw < 500:
        return "450-500"
    elif mw <= 550:
        return "500-550"
    else:
        return "550+"


def compute_empirical_prior(
    smiles: str,
    estimated_selectivity: float | None = None,
) -> EmpiricalPrior:
    """
    Compute local empirical prior P(total≥60) from official conditionals.
    
    Args:
        smiles: Canonical SMILES string
        estimated_selectivity: If known/estimated, use to refine prior.
                               For unknown molecules, assume low (conservative).
    
    Returns:
        EmpiricalPrior with expected P(≥60) and reasoning.
        
    IMPORTANT: This is NOT an official GPU score. This is a LOCAL prior only.
    """
    mw = compute_mw(smiles)
    if mw is None:
        return EmpiricalPrior(
            smiles=smiles,
            mw=0.0,
            mw_band="unknown",
            expected_p_ge_60=0.0,
            reason="invalid_structure",
            matching_conditionals=[],
        )

    band = get_mw_band(mw)
    stats = MW_BAND_STATS.get(band)
    
    matching = []
    reasons = []
    
    # Check official conditionals
    # For molecules we don't have selectivity info on, assume low-sel (conservative)
    if estimated_selectivity is None:
        estimated_selectivity = 0.0  # Assume low sel for unknown molecules
    
    in_mw_500_550 = 500 <= mw <= 550
    low_sel = estimated_selectivity < 3
    high_sel = estimated_selectivity >= 10
    
    # Apply conditionals
    if low_sel:
        # P(total≥60 | sel < 3) = 0/1169 = 0.0
        matching.append("low_selectivity_high_score")
        reasons.append(
            f"selectivity_estimate={estimated_selectivity:.1f}<3 → "
            f"P(≥60|sel<3)=0/1169=0.0 [official_leaderboard_2026_08_20]"
        )
        if in_mw_500_550:
            matching.append("mw_500_550_low_sel_high_score")
            reasons.append(
                f"MW={mw:.1f} in 500-550 AND sel<3 → "
                f"P(≥60|MW_500_550,sel<3)=0/64=0.0 [official_leaderboard_2026_08_20]"
            )
        # P(≥60) = 0 regardless of MW band
        expected_p = 0.0
    
    elif in_mw_500_550 and high_sel:
        # P(total≥60 | MW 500-550 AND sel ≥ 10) = 116/118 ≈ 0.983
        matching.append("mw_500_550_high_sel_high_score")
        reasons.append(
            f"MW={mw:.1f} in 500-550 AND sel={estimated_selectivity:.1f}≥10 → "
            f"P(≥60|MW_500_550,sel≥10)=116/118≈0.983 [official_leaderboard_2026_08_20]"
        )
        expected_p = 0.983
    
    else:
        # Fall back to MW-band statistics
        if stats is None:
            reasons.append(f"MW_band={band} has no historical data")
            expected_p = 0.0
        else:
            n = stats["n"]
            gt60 = stats["gt60"]
            median = stats["median"]
            p_ge_60 = gt60 / n if n > 0 else 0.0
            reasons.append(
                f"MW_band={band} n={n} gt60={gt60} P(≥60)={p_ge_60:.3f} "
                f"median={median:.1f} [official_leaderboard_2026_08_20]"
            )
            expected_p = p_ge_60
    
    reason = "; ".join(reasons)
    
    return EmpiricalPrior(
        smiles=smiles,
        mw=mw,
        mw_band=band,
        expected_p_ge_60=expected_p,
        reason=reason,
        matching_conditionals=matching,
        source="empirical_prior_from_official_leaderboard",
    )
