"""Discovery CLI."""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from discovery.config import Config
from discovery.feedback.store import FeedbackEntry, FeedbackStore
from discovery.gates.runner import GateRunner
from discovery.providers.base import ProviderError, ScoreResult
from discovery.providers.finalbench import FinalBenchClient, FinalBenchProvider
from discovery.providers.replay import ReplayProvider
from discovery.providers.stub import StubProvider
from discovery.scoring import passes_cutoff, rank_candidates
from discovery.scoring.prior import predict_prior
from discovery.search.evolution import EvolutionEngine
from discovery.judgment import should_submit, compute_empirical_prior
from discovery.judgment.decision import rank_candidates as rank_by_judgment

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("discovery")


def _root_from_args(args: argparse.Namespace) -> Path:
    return Path(getattr(args, "root", None) or Path.cwd())


def cmd_init(args: argparse.Namespace) -> int:
    root = _root_from_args(args)
    cfg = Config.from_env(root)
    cfg.paths.feedback.parent.mkdir(parents=True, exist_ok=True)

    client = FinalBenchClient(cfg)
    try:
        openapi = client.discover()
        seasons = client.get_seasons()
        season = client.get_season(cfg.season)
        cfg.mw_max = float(season.get("limits", {}).get("mw_max", cfg.mw_max))
        cfg.heavy_max = int(season.get("limits", {}).get("heavy_max", cfg.heavy_max))
        init_meta = {
            "base_url": cfg.base_url,
            "openapi_paths": list(openapi.get("paths", {})),
            "season": season,
            "seasons_count": len(seasons.get("seasons", [])),
            "mw_max": cfg.mw_max,
            "heavy_max": cfg.heavy_max,
        }
        meta_path = cfg.paths.root / "data" / "init.json"
        meta_path.write_text(json.dumps(init_meta, indent=2, ensure_ascii=False))
        logger.info("Initialized workspace at %s (season %s)", root, cfg.season)
        logger.info("API paths: %s", ", ".join(sorted(init_meta["openapi_paths"])))
    except ProviderError as exc:
        logger.error("Init failed: %s", exc)
        return 1
    return 0


def cmd_score(args: argparse.Namespace) -> int:
    root = _root_from_args(args)
    cfg = Config.from_env(root)
    structure = args.structure
    gate = GateRunner(cfg).check(structure)
    if not gate.passed:
        print(json.dumps({"gate_passed": False, "failures": gate.failures}, indent=2))
        return 2

    provider = ReplayProvider(cfg.paths.feedback)
    if not provider.available():
        provider = StubProvider()  # type: ignore[assignment]

    try:
        result = provider.score(gate.canonical_smiles or structure)
    except ProviderError as exc:
        print(json.dumps({"gate_passed": True, "score_error": str(exc)}, indent=2))
        return 3

    payload = {
        "smiles": result.smiles,
        "axes": result.axes,
        "total": result.total,
        "lower_bound": result.lower_bound,
        "uncertainty": result.uncertainty,
        "effective_score": result.effective_score(),
        "passes_cutoff": passes_cutoff(result),
        "official": result.official,
        "source": result.source,
    }
    print(json.dumps(payload, indent=2))
    return 0


def cmd_search(args: argparse.Namespace) -> int:
    root = _root_from_args(args)
    cfg = Config.from_env(root)
    engine = EvolutionEngine(cfg)

    score_fn = engine._try_score
    if args.mock_scores:
        score_fn = _mock_score_fn(engine.rng)

    results = engine.run(
        generations=args.generations,
        per_family=args.per_family,
        score_fn=score_fn,
    )
    total_survivors = sum(len(v) for v in results.values())
    logger.info(
        "Search complete: generation=%s survivors=%s",
        engine.state.generation,
        total_survivors,
    )
    for family, members in results.items():
        for m in members[:3]:
            logger.info(
                "  [%s] %s effective=%.2f total=%.2f",
                family,
                m.smiles[:60],
                m.effective_score(),
                m.total,
            )
    return 0


def cmd_submit(args: argparse.Namespace) -> int:
    root = _root_from_args(args)
    cfg = Config.from_env(root)
    gate = GateRunner(cfg).check(args.structure)
    if not gate.passed:
        logger.error("Gate rejected: %s", gate.failures)
        return 2

    smiles = gate.canonical_smiles or args.structure
    provider = FinalBenchProvider(cfg)
    if not provider.available():
        logger.error("Submit unavailable — set HF_TOKEN or CHALLENGE_TOKEN")
        return 3

    # Pre-submit cutoff using replay cache if available
    replay = ReplayProvider(cfg.paths.feedback)
    cached_score = None
    if replay.available():
        try:
            cached = replay.score(smiles)
            cached_score = cached.effective_score()
            if not passes_cutoff(cached):
                logger.error(
                    "Rejected: effective score %.2f <= 60",
                    cached.effective_score(),
                )
                return 4
        except ProviderError:
            pass

    # Local judgment layer check — block submission if judgment fails
    # This replaces the old MW-band median (67.6) gate with proper conditionals
    judgment = should_submit(smiles, require_warhead=False)
    if not judgment.should_submit:
        logger.error(
            "Rejected by local judgment layer: band=%s mw=%.1f empirical_P(≥60)=%.3f",
            judgment.mw_band,
            judgment.mw,
            judgment.empirical_prior_p_ge_60,
        )
        logger.error("HOLD reasons (%d): %s", len(judgment.holds), "; ".join(judgment.holds))
        return 4

    if args.dry_run:
        logger.info("Dry run OK: would submit %s", smiles)
        logger.info("Local judgment: band=%s mw=%.1f empirical_P(≥60)=%.3f [LOCAL prior, NOT official]", 
                    judgment.mw_band, judgment.mw, judgment.empirical_prior_p_ge_60)
        logger.info("Passed checks: %s", ", ".join(judgment.passes[:3]) + ("..." if len(judgment.passes) > 3 else ""))
        if cached_score is not None:
            logger.info("Replay cache: effective_score=%.1f", cached_score)
        return 0

    try:
        resp = provider.submit_candidate(
            smiles,
            args.display_name,
            model_name=args.model_name or "",
            rationale=args.rationale or "",
            visibility=args.visibility,
        )
    except ProviderError as exc:
        logger.error("Submit failed: %s", exc)
        return 5

    FeedbackStore(cfg.paths.feedback).append(
        FeedbackEntry(
            smiles=smiles,
            gate_passed=True,
            submitted=True,
            official=True,
            source="submit",
            family=args.family or "",
        )
    )
    print(json.dumps(resp, indent=2, ensure_ascii=False))
    return 0


def _mock_score_fn(rng):
    """Deterministic mock for local search demos/tests — NOT official."""

    def score(smiles: str) -> ScoreResult:
        h = sum(ord(c) for c in smiles)
        base = 40 + (h % 45)
        axes = {
            "activity": min(30, base * 0.35),
            "binding": min(20, base * 0.22),
            "selectivity": min(20, base * 0.20),
            "admet": min(15, base * 0.10),
            "novelty": min(10, base * 0.08),
            "synthesis": min(5, base * 0.05),
        }
        total = sum(axes.values())
        uncertainty = 3 + (h % 8)
        return ScoreResult(
            smiles=smiles,
            axes=axes,
            total=total,
            lower_bound=total - uncertainty,
            uncertainty=float(uncertainty),
            source="mock",
            official=False,
        )

    return score


def cmd_rank(args: argparse.Namespace) -> int:
    """
    Rank candidates using local judgment layer.
    
    This is LOCAL ranking ONLY. NOT official GPU scoring.
    Prints HOLD/SUBMIT decisions with reasons.
    """
    root = _root_from_args(args)
    cfg = Config.from_env(root)
    
    # Read candidates from file or stdin
    candidates = []
    if args.candidates_file:
        candidates_path = Path(args.candidates_file)
        if not candidates_path.exists():
            logger.error("Candidates file not found: %s", candidates_path)
            return 1
        candidates = candidates_path.read_text().strip().split("\n")
    elif args.smiles:
        candidates = args.smiles
    else:
        logger.error("Must provide --smiles or --candidates-file")
        return 1
    
    # Clean candidates
    candidates = [c.strip() for c in candidates if c.strip()]
    
    if not candidates:
        logger.error("No candidates provided")
        return 1
    
    logger.info("Ranking %d candidates (LOCAL judgment only, NOT official scores)", len(candidates))
    
    # Rank using local judgment
    ranked = rank_by_judgment(
        candidates,
        config=cfg,
        require_warhead=not args.no_warhead_check,
        use_vina=not args.no_vina,
    )
    
    # Print results
    print("\n" + "=" * 80)
    print("LOCAL JUDGMENT RANKING (NOT OFFICIAL GPU SCORES)")
    print("=" * 80 + "\n")
    
    for idx, (smiles, judgment) in enumerate(ranked, 1):
        decision = "SUBMIT" if judgment.should_submit else "HOLD"
        print(f"\n[{idx}] {decision}: {smiles[:60]}{'...' if len(smiles) > 60 else ''}")
        print(f"    MW: {judgment.mw:.1f} ({judgment.mw_band})")
        print(f"    Local Rank Score: {judgment.local_rank_score:.1f} [LOCAL metric, NOT official GPU score]")
        print(f"    Empirical P(≥60): {judgment.empirical_prior_p_ge_60:.3f} [LOCAL prior, NOT official]")
        if judgment.vina_status == "ok" and judgment.vina_kcal is not None:
            print(
                f"    Vina Pf 5TBO: {judgment.vina_kcal:.2f} kcal/mol "
                "[LOCAL AutoDock Vina, NOT official GPU score]"
            )
            if judgment.hs_kcal is not None:
                print(
                    f"    Vina Hs 4IGH: {judgment.hs_kcal:.2f} kcal/mol "
                    "[LOCAL AutoDock Vina, NOT official GPU score]"
                )
            if judgment.local_sel_kcal is not None:
                print(
                    f"    Local sel gap (Hs-Pf): {judgment.local_sel_kcal:+.2f} kcal/mol "
                    "[LOCAL docking proxy, NOT official selectivity]"
                )
        else:
            print(f"    Vina Pf/Hs: {judgment.vina_status} (no kcal, no heuristic substitute)")
        print(f"    Pharmacophore (2D): {'match' if judgment.pharmacophore_match else 'mismatch'}")
        print(f"    Warhead: {'Yes' if judgment.has_warhead else 'No'}")
        print(f"    Failed family: {'Yes (HOLD)' if judgment.is_failed_family else 'No'}")
        print(f"    DSM analogue: {'Yes (HOLD)' if judgment.is_dsm_analogue else 'No'}")
        
        if judgment.holds:
            print(f"    ❌ HOLD reasons ({len(judgment.holds)}):")
            for hold in judgment.holds:
                print(f"       - {hold}")
        
        if judgment.passes and args.verbose:
            print(f"    ✓ Passed checks ({len(judgment.passes)}):")
            for p in judgment.passes[:5]:  # Show first 5
                print(f"       - {p}")
        
        print(f"    Summary: {judgment.reasons[0] if judgment.reasons else 'N/A'}")
    
    # Summary stats
    n_submit = sum(1 for _, j in ranked if j.should_submit)
    n_hold = len(ranked) - n_submit
    
    print("\n" + "=" * 80)
    print(f"SUMMARY: {n_submit} candidates ready to SUBMIT, {n_hold} to HOLD")
    print("=" * 80 + "\n")
    print("⚠️  IMPORTANT: These are LOCAL judgments, NOT official GPU scores.")
    print("⚠️  Do NOT auto-submit based on these rankings.")
    print("⚠️  Manual review is required before any submission.\n")
    
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="discovery", description="FINAL-Bench Open Discovery harness")
    parser.add_argument("--root", type=Path, default=None, help="Project root (default: cwd)")
    sub = parser.add_subparsers(dest="command", required=True)

    p_init = sub.add_parser("init", help="Discover API and write season config")
    p_init.set_defaults(func=cmd_init)

    p_score = sub.add_parser("score", help="Gate and score a structure")
    p_score.add_argument("structure", help="SMILES or InChI")
    p_score.set_defaults(func=cmd_score)

    p_search = sub.add_parser("search", help="Run evolutionary search")
    p_search.add_argument("--generations", type=int, default=2)
    p_search.add_argument("--per-family", type=int, default=5)
    p_search.add_argument(
        "--mock-scores",
        action="store_true",
        help="Use deterministic mock scores (NOT official — local demo only)",
    )
    p_search.set_defaults(func=cmd_search)

    p_submit = sub.add_parser("submit", help="Submit candidate to FINAL-Bench")
    p_submit.add_argument("structure", help="SMILES or InChI")
    p_submit.add_argument("display_name", help="Display name on leaderboard")
    p_submit.add_argument("--model-name", default="")
    p_submit.add_argument("--rationale", default="")
    p_submit.add_argument("--visibility", default="private", choices=["private", "public"])
    p_submit.add_argument("--family", default="")
    p_submit.add_argument("--dry-run", action="store_true")
    p_submit.set_defaults(func=cmd_submit)

    p_rank = sub.add_parser("rank", help="Rank candidates using local judgment layer (NOT official scores)")
    p_rank.add_argument(
        "--smiles",
        action="extend",
        nargs="+",
        default=[],
        help="SMILES strings to rank; repeatable and accepts several per flag",
    )
    p_rank.add_argument(
        "--candidates-file",
        type=str,
        help="File with one SMILES per line",
    )
    p_rank.add_argument(
        "--no-warhead-check",
        action="store_true",
        help="Skip warhead requirement check",
    )
    p_rank.add_argument(
        "--no-vina",
        action="store_true",
        help="Skip local Vina docking (fast triage; every candidate stays on HOLD)",
    )
    p_rank.add_argument(
        "--verbose",
        action="store_true",
        help="Show detailed pass reasons",
    )
    p_rank.set_defaults(func=cmd_rank)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
