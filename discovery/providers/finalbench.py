"""FINAL-Bench API client — discovers endpoints at runtime."""

from __future__ import annotations

import logging
from typing import Any

import httpx

from discovery.config import Config
from discovery.providers.base import ProviderError, ScoreResult

logger = logging.getLogger(__name__)


class FinalBenchClient:
    """HTTP client with runtime OpenAPI discovery."""

    def __init__(self, config: Config | None = None, timeout: float = 60.0) -> None:
        self.config = config or Config.from_env()
        self.timeout = timeout
        self._openapi: dict[str, Any] | None = None
        self._paths: set[str] | set = set()

    def _headers(self) -> dict[str, str]:
        headers: dict[str, str] = {"Accept": "application/json"}
        token = self.config.challenge_token or self.config.hf_token
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def discover(self) -> dict[str, Any]:
        if self._openapi is not None:
            return self._openapi
        candidates = [
            f"{self.config.base_url}/openapi.json",
            f"{self.config.base_url}/gradio_api/openapi.json",
        ]
        last_error: Exception | None = None
        for url in candidates:
            try:
                resp = httpx.get(url, timeout=self.timeout)
                if resp.status_code == 200:
                    self._openapi = resp.json()
                    self._paths = set(self._openapi.get("paths", {}))
                    logger.info("Discovered OpenAPI at %s (%d paths)", url, len(self._paths))
                    return self._openapi
            except Exception as exc:  # noqa: BLE001
                last_error = exc
        raise ProviderError(f"Could not discover OpenAPI: {last_error}")

    def has_path(self, path: str) -> bool:
        self.discover()
        return path in self._paths

    def get_seasons(self) -> dict[str, Any]:
        if not self.has_path("/api/seasons"):
            raise ProviderError("/api/seasons not available")
        resp = httpx.get(
            f"{self.config.base_url}/api/seasons",
            headers=self._headers(),
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def get_season(self, season: int | None = None) -> dict[str, Any]:
        season = season or self.config.season
        if self.has_path("/api/season"):
            resp = httpx.get(
                f"{self.config.base_url}/api/season",
                params={"season": season},
                headers=self._headers(),
                timeout=self.timeout,
            )
            resp.raise_for_status()
            return resp.json()
        raise ProviderError("/api/season not available")

    def get_leaderboard(self, season: int | None = None) -> dict[str, Any]:
        season = season or self.config.season
        if not self.has_path("/api/leaderboard"):
            raise ProviderError("/api/leaderboard not available")
        resp = httpx.get(
            f"{self.config.base_url}/api/leaderboard",
            params={"season": season},
            headers=self._headers(),
            timeout=self.timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def submit(
        self,
        structure: str,
        display_name: str,
        *,
        model_name: str = "",
        rationale: str = "",
        visibility: str = "private",
        season: int | None = None,
    ) -> dict[str, Any]:
        if not self.has_path("/api/submit"):
            raise ProviderError("/api/submit not available")
        token = self.config.challenge_token or self.config.hf_token
        if not token:
            raise ProviderError(
                "Submit requires HF_TOKEN or CHALLENGE_TOKEN in environment"
            )
        payload = {
            "structure": structure,
            "display_name": display_name,
            "model_name": model_name,
            "rationale": rationale,
            "visibility": visibility,
            "season": season or self.config.season,
        }
        resp = httpx.post(
            f"{self.config.base_url}/api/submit",
            json=payload,
            headers=self._headers(),
            timeout=self.timeout,
        )
        if resp.status_code == 401:
            raise ProviderError("Authentication failed — Hugging Face login required")
        resp.raise_for_status()
        return resp.json()


class FinalBenchProvider:
    """Uses FINAL-Bench API. Official scoring requires authenticated submit."""

    name = "finalbench"

    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config.from_env()
        self.client = FinalBenchClient(self.config)

    def available(self) -> bool:
        token = self.config.challenge_token or self.config.hf_token
        if not token:
            return False
        try:
            self.client.discover()
            return self.client.has_path("/api/submit")
        except ProviderError:
            return False

    def score(self, smiles: str) -> ScoreResult:
        """Official local score endpoint does not exist — submit is required."""
        raise ProviderError(
            "FINAL-Bench has no public /api/score endpoint. "
            "Use `discovery submit` with HF_TOKEN, then replay from feedback."
        )

    def submit_candidate(
        self,
        smiles: str,
        display_name: str,
        **kwargs: Any,
    ) -> dict[str, Any]:
        return self.client.submit(smiles, display_name, **kwargs)

    @staticmethod
    def leaderboard_entry_to_score(entry: dict[str, Any], smiles: str) -> ScoreResult:
        axes = entry.get("axes") or {}
        total = float(entry.get("total", 0.0))
        detail = entry.get("detail") or {}
        uncertainty = _estimate_uncertainty(detail)
        lower = total - uncertainty if uncertainty is not None else None
        return ScoreResult(
            smiles=smiles,
            axes={k: float(v) for k, v in axes.items()},
            total=total,
            lower_bound=lower,
            uncertainty=uncertainty,
            source="finalbench",
            official=True,
        )


def _estimate_uncertainty(detail: dict[str, Any]) -> float | None:
    """Derive uncertainty from repeat spreads when present."""
    spreads: list[float] = []
    run = detail.get("run") or {}
    for key in ("repeats_pf", "repeats_hs"):
        block = run.get(key) or detail.get(key)
        if isinstance(block, dict) and "spread" in block:
            spreads.append(float(block["spread"]))
    if not spreads:
        return None
    # Map biophysical spread to conservative score interval (heuristic envelope).
    return min(15.0, max(spreads) * 50.0)
