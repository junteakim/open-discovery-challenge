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

    # MW-band prior check — block submission if prior lower_bound ≤ 60
    # This runs even when no replay cache exists
    prior = predict_prior(smiles)
    if prior.lower_bound <= 60.0:
        logger.error(
            "Rejected by MW-band prior: band=%s mw=%.1f prior_lower_bound=%.1f cutoff=60.0",
            prior.mw_band,
            prior.mw,
            prior.lower_bound,
        )
        logger.error("Reason: %s", prior.reason)
        return 4

    if args.dry_run:
        logger.info("Dry run OK: would submit %s", smiles)
        logger.info("MW-band prior: band=%s mw=%.1f lower_bound=%.1f", prior.mw_band, prior.mw, prior.lower_bound)
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

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
