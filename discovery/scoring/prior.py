"""MW-band-based local prior for pre-submit filtering."""

from __future__ import annotations

from dataclasses import dataclass

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors
except ImportError:  # pragma: no cover
    Chem = None
    Descriptors = None


# Season 1 official leaderboard observations:
# MW ≤300 has NEVER scored >60 (band max 41.4)
# MW 450-550 concentrates scores >60 (500-550 median 67.6)
MW_BAND_STATS = {
    "0-300": {"max_observed": 41.4, "has_over_60": False},
    "300-450": {"max_observed": 58.0, "has_over_60": False},
    "450-500": {"max_observed": 68.0, "has_over_60": True, "p10": 61.5},
    "500-550": {"max_observed": 72.0, "has_over_60": True, "p10": 63.0},
}


@dataclass
class PriorResult:
    smiles: str
    mw: float
    mw_band: str
    predicted_total: float
    lower_bound: float
    reason: str
    source: str = "mw_band_prior"


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
    if mw < 300:
        return "0-300"
    elif mw < 450:
        return "300-450"
    elif mw < 500:
        return "450-500"
    elif mw <= 550:
        return "500-550"
    else:
        return "550+"


def predict_prior(smiles: str, leaderboard_stats: dict | None = None) -> PriorResult:
    """
    Return local prior prediction based on MW band and optional live leaderboard stats.
    
    Conservative policy:
    - If the candidate's MW band has 0 official entries >60, lower_bound = historical max (or 0)
    - If the band has entries >60, lower_bound = cautious percentile (p10)
    - NEVER invent an official GPU score — this is a LOCAL PRIOR only
    
    Args:
        smiles: Canonical SMILES string
        leaderboard_stats: Optional dict of live leaderboard statistics (unused in v1, reserved for future)
    
    Returns:
        PriorResult with predicted_total, lower_bound, mw_band, and reason
    """
    mw = compute_mw(smiles)
    if mw is None:
        # Invalid structure — return pessimistic prior
        return PriorResult(
            smiles=smiles,
            mw=0.0,
            mw_band="unknown",
            predicted_total=0.0,
            lower_bound=0.0,
            reason="invalid_structure",
        )
    
    band = get_mw_band(mw)
    stats = MW_BAND_STATS.get(band)
    
    if stats is None:
        # Band >550 — no historical data, pessimistic default
        return PriorResult(
            smiles=smiles,
            mw=mw,
            mw_band=band,
            predicted_total=40.0,
            lower_bound=30.0,
            reason=f"mw_band={band} has no historical data, pessimistic default",
        )
    
    if not stats["has_over_60"]:
        # Band has NEVER scored >60 — use historical max as both prediction and lower bound
        max_obs = stats["max_observed"]
        return PriorResult(
            smiles=smiles,
            mw=mw,
            mw_band=band,
            predicted_total=max_obs,
            lower_bound=max_obs,
            reason=f"mw_band={band} has NEVER scored >60 (historical max {max_obs:.1f})",
        )
    
    # Band has entries >60 — use p10 as conservative lower bound
    p10 = stats.get("p10", stats["max_observed"] * 0.85)
    max_obs = stats["max_observed"]
    predicted = (p10 + max_obs) / 2  # midpoint estimate
    
    return PriorResult(
        smiles=smiles,
        mw=mw,
        mw_band=band,
        predicted_total=predicted,
        lower_bound=p10,
        reason=f"mw_band={band} has entries >60 (p10={p10:.1f})",
    )
