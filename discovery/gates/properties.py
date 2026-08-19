"""Molecular property checks for gates."""

from __future__ import annotations

try:
    from rdkit import Chem
    from rdkit.Chem import Crippen, Descriptors, Lipinski
except ImportError:  # pragma: no cover
    Chem = None
    Crippen = None
    Descriptors = None
    Lipinski = None

# Structural alerts loosely associated with mutagenicity (gate, not official score).
AMES_ALERT_SMARTS = [
    "a1aaaaa1N=N",  # aromatic azo
    "[N+](=O)[O-]",  # nitro
    "N=N",  # diazo
]

# Known antimalarial / PfDHODH reference scaffolds — reject close analogues (scaffold hop rule).
KNOWN_ANTIMALARIAL_SMILES = [
    # DSM265
    "Cc1nc(N2CCOCC2)c2nc(Nc3ccc(C#N)c(F)c3)nc(N)c2n1",
    # ODS009 / close triazolopyrimidine series representative
    "COc1cc(Nc2nc(N)nc3c2ncn3C2CCNCC2)ccc1C#N",
    # Atovaquone-like naphthoquinone
    "CC(C)Cc1ccc(C(=O)c2ccc(O)c(C(=O)C3CC3)c2O)cc1",
    # Chloroquine
    "CCN(CC)CCCC(C)Nc1ccnc2cc(Cl)ccc12",
]

TANIMOTO_ANALOGUE_THRESHOLD = 0.45


def compute_properties(smiles: str) -> dict[str, float | int | None]:
    if Chem is None:
        return {}
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return {}
    return {
        "mw": Descriptors.MolWt(mol),
        "heavy_atoms": mol.GetNumHeavyAtoms(),
        "logp": Crippen.MolLogP(mol),
        "tpsa": Descriptors.TPSA(mol),
        "hbd": Lipinski.NumHDonors(mol),
        "hba": Lipinski.NumHAcceptors(mol),
    }


def mutagenicity_alerts(smiles: str) -> list[str]:
    if Chem is None:
        return []
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return ["invalid_structure"]
    hits: list[str] = []
    for smarts in AMES_ALERT_SMARTS:
        pat = Chem.MolFromSmarts(smarts)
        if pat is not None and mol.HasSubstructMatch(pat):
            hits.append(f"ames_alert:{smarts}")
    return hits


def extreme_insolubility(props: dict) -> bool:
    """Reject likely extreme insolubility before scoring."""
    logp = props.get("logp")
    tpsa = props.get("tpsa")
    mw = props.get("mw")
    if logp is None or tpsa is None or mw is None:
        return False
    # Very lipophilic, low polarity, high MW → precipitation risk
    return logp > 6.5 and tpsa < 40 and mw > 400
