"""Gate orchestration — reject before any scoring."""

from __future__ import annotations

from discovery.chemistry.fingerprints import max_similarity, morgan_fp, tanimoto
from discovery.chemistry.smiles import validate_structure
from discovery.config import Config
from discovery.gates.result import GateResult
from discovery.gates.pains import pains_matches
from discovery.gates.properties import (
    KNOWN_ANTIMALARIAL_SMILES,
    TANIMOTO_ANALOGUE_THRESHOLD,
    compute_properties,
    extreme_insolubility,
    mutagenicity_alerts,
)
from discovery.gates.warheads import warhead_matches

DUPLICATE_TANIMOTO = 0.95


class GateRunner:
    def __init__(self, config: Config | None = None) -> None:
        self.config = config or Config.from_env()
        self._seen_fps: list = []
        self._seen_smiles: set[str] = set()

    def register(self, canonical_smiles: str) -> None:
        self._seen_smiles.add(canonical_smiles)
        fp = morgan_fp(canonical_smiles)
        if fp is not None:
            self._seen_fps.append(fp)

    def check(self, structure: str) -> GateResult:
        failures: list[str] = []

        valid, canonical = validate_structure(structure)
        if not valid or canonical is None:
            return GateResult(passed=False, failures=["invalid_smiles_or_inchi"])

        if canonical in self._seen_smiles:
            failures.append("duplicate_smiles")

        for fp in self._seen_fps:
            current = morgan_fp(canonical)
            if current is not None and tanimoto(current, fp) >= DUPLICATE_TANIMOTO:
                failures.append("duplicate_fingerprint")
                break

        props = compute_properties(canonical)
        mw = props.get("mw")
        heavy = props.get("heavy_atoms")
        if mw is not None and mw > self.config.mw_max:
            failures.append(f"mw_over_cap:{mw:.1f}>{self.config.mw_max}")
        if heavy is not None and heavy > self.config.heavy_max:
            failures.append(f"heavy_atoms_over_cap:{heavy}>{self.config.heavy_max}")

        failures.extend(f"pains:{h}" for h in pains_matches(canonical))
        failures.extend(f"warhead:{h}" for h in warhead_matches(canonical))
        failures.extend(mutagenicity_alerts(canonical))

        if extreme_insolubility(props):
            failures.append("extreme_insolubility")

        sim = max_similarity(canonical, KNOWN_ANTIMALARIAL_SMILES)
        if sim >= TANIMOTO_ANALOGUE_THRESHOLD:
            failures.append(f"known_antimalarial_analogue:tanimoto={sim:.3f}")

        passed = len(failures) == 0
        return GateResult(passed=passed, failures=failures, canonical_smiles=canonical)


def run_gates(structure: str, config: Config | None = None) -> GateResult:
    return GateRunner(config).check(structure)
