"""PAINS filter using RDKit FilterCatalog."""

from __future__ import annotations

try:
    from rdkit import Chem
    from rdkit.Chem.FilterCatalog import FilterCatalog, FilterCatalogParams
except ImportError:  # pragma: no cover
    Chem = None
    FilterCatalog = None
    FilterCatalogParams = None

_CATALOG = None


def _catalog():
    global _CATALOG
    if _CATALOG is None and FilterCatalog is not None:
        params = FilterCatalogParams()
        params.AddCatalog(FilterCatalogParams.FilterCatalogs.PAINS)
        params.AddCatalog(FilterCatalogParams.FilterCatalogs.PAINS_A)
        params.AddCatalog(FilterCatalogParams.FilterCatalogs.PAINS_B)
        params.AddCatalog(FilterCatalogParams.FilterCatalogs.PAINS_C)
        _CATALOG = FilterCatalog(params)
    return _CATALOG


def pains_matches(smiles: str) -> list[str]:
    if Chem is None:
        return []
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return ["invalid_structure"]
    catalog = _catalog()
    if catalog is None:
        return []
    hits = catalog.GetMatches(mol)
    return [entry.GetDescription() for entry in hits]
