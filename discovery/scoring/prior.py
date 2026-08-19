"""MW-band-based local prior for pre-submit filtering."""

from __future__ import annotations

from dataclasses import dataclass

try:
    from rdkit import Chem
    from rdkit.Chem import Descriptors
except ImportError:  # pragma: no cover
    Chem = None
    Descriptors = None


# Season 1 official leaderboard stats (2026-08-19)
# Live official totals by MW band: n, median, p10, max, count>60
# Source: /api/leaderboard?season=1
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


def predict_prior(smiles: str, leaderboard_stats: dict | None = None) -> PriorResult:
    """
    Return local prior prediction based on MW band and optional live leaderboard stats.
    
    Honest, conservative policy (2026-08-19 live leaderboard):
    - lower_bound = band median (not p10, not invented values)
    - Only bands with median >60 can pass the ≤60 cutoff
    - As of 2026-08-19, only 500-550 band has median >60 (67.6)
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
        # Band with no historical data (<150 or >550) — pessimistic default
        return PriorResult(
            smiles=smiles,
            mw=mw,
            mw_band=band,
            predicted_total=30.0,
            lower_bound=30.0,
            reason=f"mw_band={band} has no historical data, pessimistic default",
        )
    
    # Use median as conservative lower_bound
    # Predicted total = midpoint between median and max
    median = stats["median"]
    max_obs = stats["max"]
    n = stats["n"]
    gt60 = stats["gt60"]
    
    predicted = (median + max_obs) / 2
    
    return PriorResult(
        smiles=smiles,
        mw=mw,
        mw_band=band,
        predicted_total=predicted,
        lower_bound=median,
        reason=f"mw_band={band} n={n} median={median:.1f} max={max_obs:.1f} (gt60={gt60})",
    )
