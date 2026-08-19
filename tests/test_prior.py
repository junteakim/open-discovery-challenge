"""Tests for MW-band prior."""

from discovery.scoring.prior import predict_prior, get_mw_band, compute_mw


def test_small_molecule_low_prior():
    """MW 174-265 seeds should have prior ≤60 and be blocked."""
    # Simple amide ~200 Da
    smiles = "CC(=O)Nc1ccccc1"  # acetanilide, ~135 Da
    prior = predict_prior(smiles)
    assert prior.mw < 300
    assert prior.mw_band == "0-300"
    assert prior.lower_bound <= 60, f"Expected prior ≤60 for small MW, got {prior.lower_bound}"
    assert "NEVER scored >60" in prior.reason


def test_competitive_band_not_auto_dropped():
    """MW 450-550 band molecules should not be auto-dropped solely for size."""
    # Larger scaffold in competitive range (~500 Da)
    # benzimidazole with heavier substituents
    smiles = "c1ccc2[nH]c(C(=O)NCCOC)nc2c1c1ccc(OC)c(c1)c1ccc2ccccc2c1"
    prior = predict_prior(smiles)
    
    # Should be in competitive band
    assert 450 <= prior.mw <= 550, f"Expected MW 450-550, got {prior.mw}"
    assert prior.mw_band in ["450-500", "500-550"]
    
    # Should have entries >60 in historical data
    assert prior.lower_bound > 60, f"Expected prior >60 for competitive band, got {prior.lower_bound}"
    assert "has entries >60" in prior.reason


def test_mw_band_classification():
    """Test MW band boundaries."""
    assert get_mw_band(150) == "0-300"
    assert get_mw_band(299.9) == "0-300"
    assert get_mw_band(300) == "300-450"
    assert get_mw_band(449.9) == "300-450"
    assert get_mw_band(450) == "450-500"
    assert get_mw_band(499.9) == "450-500"
    assert get_mw_band(500) == "500-550"
    assert get_mw_band(550) == "500-550"
    assert get_mw_band(551) == "550+"


def test_invalid_structure_pessimistic():
    """Invalid structures get pessimistic prior."""
    prior = predict_prior("not_a_smiles!!!")
    assert prior.lower_bound == 0.0
    assert prior.reason == "invalid_structure"


def test_prior_source_label():
    """Prior results must be labeled as local, not official."""
    smiles = "CCO"
    prior = predict_prior(smiles)
    assert prior.source == "mw_band_prior"
    # Never claim to be official
    assert "official" not in prior.source.lower()
