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
from discovery.judgment.pocket import check_pocket_pharmacophore
from discovery.judgment.dock import dock_smiles, vina_available


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
    
    # Vina docking results (LOCAL only, not official)
    vina_status: str = "unavailable"
    vina_kcal: float | None = None
    
    # Local rank score (for sorting HOLD candidates, NOT an official score)
    # Higher is better. Combines: distance from failed families, DSM distance,
    # warhead presence, MW in range, gate pass, pharmacophore, vina affinity
    local_rank_score: float = 0.0
    
    source: str = "local_judgment_layer"


def should_submit(
    smiles: str,
    config: Config | None = None,
    gate_runner: GateRunner | None = None,
    require_warhead: bool = True,
    estimated_selectivity: float | None = None,
    use_vina: bool = True,
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
    6. Pharmacophore match (aromatic + HBA for HIS185/ARG265)
    7. Vina docking available and status == "ok"
    
    MW 500-550 alone is NEVER sufficient for submit.
    
    Args:
        smiles: Candidate SMILES
        config: Optional Config
        gate_runner: Optional GateRunner (will create if None)
        require_warhead: Whether to require warhead presence
        estimated_selectivity: Optional selectivity estimate for prior
        use_vina: Run local Vina docking. Skipping it never grants points and
            always keeps the candidate on HOLD.
    
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
    
    # Check 6: Pharmacophore (PfDHODH pocket awareness)
    pharma_result = check_pocket_pharmacophore(canonical)
    pharma_passes = pharma_result["pass"]
    
    if not pharma_passes:
        holds.append(f"pharmacophore_fail:{pharma_result['reason']}")
        reasons.append(f"HOLD: Pharmacophore mismatch (no HBA/aromatic for HIS185/ARG265)")
    else:
        passes.append(f"pharmacophore_ok:aromatic={pharma_result['aromatic_rings']},hba={pharma_result['hba']}")
    
    # Check 7: Vina docking
    vina_status = "unavailable"
    vina_kcal = None
    
    if not use_vina:
        vina_status = "skipped"
        holds.append("vina_skipped:no_heuristic")
        reasons.append("HOLD: Vina docking skipped")
    elif vina_available():
        dock_result = dock_smiles(canonical)
        vina_status = dock_result["status"]
        vina_kcal = dock_result["kcal"]
        
        if vina_status == "ok" and vina_kcal is not None:
            passes.append(f"vina_ok:{vina_kcal:.2f}kcal/mol")
        else:
            holds.append(f"vina_{vina_status}:{dock_result.get('reason', 'unknown')}")
            reasons.append(f"HOLD: Vina docking failed or not available")
    else:
        holds.append("vina_unavailable:no_binary_or_receptor")
        reasons.append("HOLD: Vina not available")
    
    # MW-only check: MW 500-550 alone is NEVER sufficient
    if 500 <= mw <= 550 and len(holds) == 0:
        # All checks passed, but let's make sure it's not just MW-band
        if empirical_p <= 0.5:  # Low prior even in good MW band
            holds.append(f"mw_500_550_but_low_prior:p={empirical_p:.3f}")
            reasons.append("HOLD: MW 500-550 alone is insufficient (low prior)")
    
    # Decision: ALL checks must pass, including vina
    can_submit = (
        len(holds) == 0 
        and gate_passed 
        and vina_status == "ok"
    )
    
    if can_submit:
        reasons.append(f"SUBMIT: All checks passed (n_checks={len(passes)})")
    elif not reasons:
        reasons.append("HOLD: Default (not all conditions met)")
    
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
    
    # Pharmacophore match (+15 if passes)
    if pharma_passes:
        local_rank += 15.0
    
    # Vina docking affinity (+20 max, only if status == "ok")
    if vina_status == "ok" and vina_kcal is not None:
        # More negative affinity = better
        # Scale: -10 kcal/mol → +20 pts, 0 kcal/mol → 0 pts
        affinity_score = max(0, min(20, -vina_kcal * 2))
        local_rank += affinity_score
    # If vina unavailable or failed: no points added (no fake heuristic)
    
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
        vina_status=vina_status,
        vina_kcal=vina_kcal,
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
    use_vina: bool = True,
) -> list[tuple[str, JudgmentResult]]:
    """
    Rank a list of candidates by local judgment.
    
    Returns list of (smiles, JudgmentResult) sorted by:
    1. should_submit (True first)
    2. local_rank_score (higher first)
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
            use_vina=use_vina,
        )
        results.append((smiles, judgment))
    
    # Sort: submit first, then by local rank score, then by smiles
    results.sort(
        key=lambda x: (
            -int(x[1].should_submit),  # True first (negative to reverse)
            -x[1].local_rank_score,  # Higher rank first
            x[0],  # Stable sort by SMILES
        )
    )
    
    return results
