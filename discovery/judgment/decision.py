"""Local decision module: should_submit gate with documented reasoning.

This module provides LOCAL ranking ONLY. It does NOT produce official GPU scores.
Default is HOLD unless ALL conditions pass.
"""

from __future__ import annotations

from dataclasses import dataclass

from discovery.chemistry.fingerprints import max_similarity
from discovery.config import Config
from discovery.gates.properties import KNOWN_ANTIMALARIAL_SMILES, TANIMOTO_ANALOGUE_THRESHOLD
from discovery.gates.runner import GateRunner
from discovery.judgment.empirical_prior import compute_empirical_prior
from discovery.judgment.failed_families import check_failed_family
from discovery.judgment.warhead_generator import has_warhead
from discovery.judgment.pocket import check_pfdhod_pharmacophore
from discovery.judgment.dock import dock_molecule, estimate_binding_potential


@dataclass
class JudgmentResult:
    """Local judgment result (NOT an official score)."""
    
    smiles: str
    should_submit: bool
    reasons: list[str]
    holds: list[str]  # Reasons to HOLD
    passes: list[str]  # What passed
    
    # Individual check results
    gate_passed: bool
    empirical_prior_p_ge_60: float
    is_failed_family: bool
    is_dsm_analogue: bool
    has_warhead: bool
    
    # Metadata
    mw: float
    mw_band: str
    pharmacophore_match: bool = False
    
    # Local rank score (for sorting HOLD candidates, NOT an official score)
    # Higher is better. Combines: distance from failed families, DSM distance,
    # warhead presence, MW in range, gate pass, pharmacophore, binding estimate
    local_rank_score: float = 0.0
    
    source: str = "local_judgment_layer"


def should_submit(
    smiles: str,
    config: Config | None = None,
    gate_runner: GateRunner | None = None,
    require_warhead: bool = True,
    estimated_selectivity: float | None = None,
) -> JudgmentResult:
    """
    Decide whether to submit a candidate based on LOCAL judgment.
    
    This is NOT an official scorer. This is a local filter.
    Default is HOLD unless ALL conditions pass.
    
    Conditions (ALL must pass):
    1. Gates pass (MW≤550, heavy≤45, PAINS, parse, etc.)
    2. NOT failed-family analogue (Tanimoto < 0.60 vs known failures)
    3. NOT DSM/antimalarial analogue (Tanimoto < 0.45 vs known antimalarials)
    4. Has required warhead (if require_warhead=True)
    5. Empirical prior P(≥60) > 0 (NOT the sel<3 bucket)
    
    MW 500-550 alone is NEVER sufficient for submit.
    
    Args:
        smiles: Candidate SMILES
        config: Optional Config
        gate_runner: Optional GateRunner (will create if None)
        require_warhead: Whether to require warhead presence
        estimated_selectivity: Optional selectivity estimate for prior
    
    Returns:
        JudgmentResult with should_submit bool and detailed reasons
    """
    config = config or Config.from_env()
    gate_runner = gate_runner or GateRunner(config)
    
    reasons = []
    holds = []
    passes = []
    
    # Check 1: Gates
    gate_result = gate_runner.check(smiles)
    gate_passed = gate_result.passed
    canonical = gate_result.canonical_smiles or smiles
    
    if not gate_passed:
        holds.append(f"gate_failed:{','.join(gate_result.failures)}")
        reasons.append("HOLD: Gate failures")
    else:
        passes.append("gate_passed")
    
    # Check 2: Empirical prior
    prior = compute_empirical_prior(canonical, estimated_selectivity=estimated_selectivity)
    empirical_p = prior.expected_p_ge_60
    mw = prior.mw
    mw_band = prior.mw_band
    
    if empirical_p <= 0.0:
        holds.append(f"empirical_prior_p_ge_60=0.0:{prior.reason}")
        reasons.append(f"HOLD: Empirical P(≥60)=0 (likely sel<3 bucket)")
    else:
        passes.append(f"empirical_prior_p_ge_60={empirical_p:.3f}")
    
    # Check 3: Failed family
    failed_check = check_failed_family(canonical)
    is_failed = not failed_check["passed"]
    
    if is_failed:
        holds.append(f"failed_family_analogue:{failed_check['reason']}")
        reasons.append(f"HOLD: Too similar to failed family")
    else:
        passes.append(f"failed_family_check_passed:max_sim={failed_check['max_similarity']:.3f}")
    
    # Check 4: DSM/antimalarial analogue
    dsm_sim = max_similarity(canonical, KNOWN_ANTIMALARIAL_SMILES)
    is_dsm = dsm_sim >= TANIMOTO_ANALOGUE_THRESHOLD
    
    if is_dsm:
        holds.append(f"dsm_antimalarial_analogue:tanimoto={dsm_sim:.3f}")
        reasons.append(f"HOLD: DSM/antimalarial analogue")
    else:
        passes.append(f"dsm_check_passed:tanimoto={dsm_sim:.3f}")
    
    # Check 5: Warhead (if required)
    has_wh, warhead_types = has_warhead(canonical)
    
    if require_warhead and not has_wh:
        holds.append("no_warhead")
        reasons.append("HOLD: Required warhead not present")
    elif has_wh:
        passes.append(f"warhead_present:{','.join(warhead_types)}")
    else:
        passes.append("warhead_not_required")
    
    # MW-only check: MW 500-550 alone is NEVER sufficient
    if 500 <= mw <= 550 and len(holds) == 0:
        # All checks passed, but let's make sure it's not just MW-band
        if empirical_p <= 0.5:  # Low prior even in good MW band
            holds.append(f"mw_500_550_but_low_prior:p={empirical_p:.3f}")
            reasons.append("HOLD: MW 500-550 alone is insufficient (low prior)")
    
    # Decision
    can_submit = len(holds) == 0 and gate_passed
    
    if can_submit:
        reasons.append(f"SUBMIT: All checks passed (n_checks={len(passes)})")
    elif not reasons:
        reasons.append("HOLD: Default (not all conditions met)")
    
    # Check pharmacophore (PfDHODH pocket awareness)
    pharma_result = check_pfdhod_pharmacophore(canonical)
    pharma_passes = pharma_result["passes"]
    
    # Check docking (if available)
    dock_result = dock_molecule(canonical)
    dock_status = dock_result.get("status", "unavailable")
    dock_affinity = dock_result.get("kcal")
    
    # Estimate binding potential (rough heuristic, not actual docking)
    binding_estimate = estimate_binding_potential(canonical)
    
    # Compute local rank score (for sorting HOLD candidates)
    # This is NOT an official score, just for internal ranking
    local_rank = 0.0
    
    # Base: gate pass (+10)
    if gate_passed:
        local_rank += 10.0
    
    # Distance from failed families (+20 for low similarity)
    local_rank += (1.0 - failed_check["max_similarity"]) * 20.0
    
    # Distance from DSM (+15 for low similarity)
    local_rank += (1.0 - dsm_sim) * 15.0
    
    # Has warhead (+10)
    if has_wh:
        local_rank += 10.0
    
    # MW in target range 300-550 (+10)
    if 300 <= mw <= 550:
        local_rank += 10.0
    
    # Pharmacophore match (+15 if passes, otherwise 0)
    # This separates random alkyl-pyrazoles from pocket-aware designs
    if pharma_passes:
        local_rank += 15.0
        passes.append(f"pharmacophore_match:{pharma_result['features']}")
    else:
        holds.append(f"pharmacophore_fail:{pharma_result['reason']}")
    
    # Docking or binding estimate (+20 max)
    if dock_status == "success" and dock_affinity is not None:
        # More negative affinity = better
        # Scale: -10 kcal/mol → +20 pts, 0 kcal/mol → 0 pts
        affinity_score = max(0, min(20, -dock_affinity * 2))
        local_rank += affinity_score
        passes.append(f"docking_5tbo:{dock_affinity:.1f}kcal/mol")
    else:
        # Use binding estimate (0-20) when docking unavailable
        local_rank += binding_estimate
        if dock_status != "success":
            passes.append(f"docking_unavailable:fallback_estimate:{binding_estimate:.1f}/20")
        else:
            passes.append(f"binding_estimate:{binding_estimate:.1f}/20")
    
    # Empirical prior (scaled to max +20, but only if positive)
    if empirical_p > 0:
        local_rank += min(empirical_p * 20, 20.0)
    
    return JudgmentResult(
        smiles=canonical,
        should_submit=can_submit,
        reasons=reasons,
        holds=holds,
        passes=passes,
        gate_passed=gate_passed,
        empirical_prior_p_ge_60=empirical_p,
        is_failed_family=is_failed,
        is_dsm_analogue=is_dsm,
        has_warhead=has_wh,
        pharmacophore_match=pharma_passes,
        mw=mw,
        mw_band=mw_band,
        local_rank_score=local_rank,
        source="local_judgment_layer",
    )


def rank_candidates(
    candidates: list[str],
    config: Config | None = None,
    gate_runner: GateRunner | None = None,
    require_warhead: bool = True,
) -> list[tuple[str, JudgmentResult]]:
    """
    Rank a list of candidates by local judgment.
    
    Returns list of (smiles, JudgmentResult) sorted by:
    1. should_submit (True first)
    2. empirical_prior_p_ge_60 (higher first)
    3. SMILES (for stable sort)
    
    This is LOCAL ranking only, not official scoring.
    """
    config = config or Config.from_env()
    gate_runner = gate_runner or GateRunner(config)
    
    results = []
    for smiles in candidates:
        judgment = should_submit(
            smiles,
            config=config,
            gate_runner=gate_runner,
            require_warhead=require_warhead,
        )
        results.append((smiles, judgment))
    
    # Sort: submit first, then by local rank score, then by smiles
    results.sort(
        key=lambda x: (
            -int(x[1].should_submit),  # True first (negative to reverse)
            -x[1].local_rank_score,  # Higher rank first (uses distance, warhead, MW, etc.)
            x[0],  # Stable sort by SMILES
        )
    )
    
    return results
