"""Tests for MW-band prior."""

from discovery.scoring.prior import predict_prior, get_mw_band, compute_mw


def test_small_molecule_low_prior():
    """MW <300 seeds should have median ≤60 and be blocked."""
    # Simple amide ~135 Da
    smiles = "CC(=O)Nc1ccccc1"  # acetanilide, ~135 Da
    prior = predict_prior(smiles)
    assert prior.mw < 150
    assert prior.mw_band == "<150"
    assert prior.lower_bound <= 60, f"Expected prior ≤60 for small MW, got {prior.lower_bound}"


def test_450da_molecule_fails_prior():
    """MW ~450 Da in 450-500 band must FAIL (median 42.6 ≤60)."""
    # Molecule in 450-500 band
    smiles = "c1ccc2[nH]c(C(=O)NCCOC)nc2c1c1ccc(OC)c(c1)c1ccc2ccccc2c1"
    prior = predict_prior(smiles)
    
    # Should be in 450-500 band
    assert 450 <= prior.mw < 500, f"Expected MW 450-500, got {prior.mw}"
    assert prior.mw_band == "450-500"
    
    # Median is 42.6, so should be rejected
    assert prior.lower_bound <= 60, f"Expected prior ≤60 for 450-500 band (median 42.6), got {prior.lower_bound}"
    assert "median=42.6" in prior.reason


def test_520da_molecule_passes_prior():
    """MW ~520 Da in 500-550 band should pass (median 67.6 >60)."""
    # Molecule in 500-550 band (~512 Da)
    smiles = "c1ccc2[nH]c(C(=O)NCCc3ccccc3)nc2c1c1ccc(OC)c(C)c1c1ccc2ccccc2c1"
    prior = predict_prior(smiles)
    
    # Should be in 500-550 band
    assert 500 <= prior.mw <= 550, f"Expected MW 500-550, got {prior.mw}"
    assert prior.mw_band == "500-550"
    
    # Median is 67.6, so should pass
    assert prior.lower_bound > 60, f"Expected prior >60 for 500-550 band (median 67.6), got {prior.lower_bound}"
    assert "median=67.6" in prior.reason


def test_mw_band_classification():
    """Test MW band boundaries with real leaderboard bands."""
    assert get_mw_band(140) == "<150"
    assert get_mw_band(150) == "150-200"
    assert get_mw_band(199.9) == "150-200"
    assert get_mw_band(200) == "200-250"
    assert get_mw_band(249.9) == "200-250"
    assert get_mw_band(250) == "250-300"
    assert get_mw_band(299.9) == "250-300"
    assert get_mw_band(300) == "300-350"
    assert get_mw_band(349.9) == "300-350"
    assert get_mw_band(350) == "350-400"
    assert get_mw_band(399.9) == "350-400"
    assert get_mw_band(400) == "400-450"
    assert get_mw_band(449.9) == "400-450"
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


def test_300_350_band_has_low_median():
    """300-350 band has median 18.0, should be rejected despite having 5 >60 outliers."""
    # Molecule in 300-350 band
    smiles = "c1ccc2c(c1)nc(NC(=O)NCC)nc2c1ccc(OC)cc1"
    prior = predict_prior(smiles)
    
    assert 300 <= prior.mw < 350, f"Expected MW 300-350, got {prior.mw}"
    assert prior.mw_band == "300-350"
    # Median is 18.0, should be rejected
    assert prior.lower_bound <= 60, f"Expected prior ≤60 (median 18.0), got {prior.lower_bound}"
    assert "gt60=5" in prior.reason  # Has 5 outliers but median is still low
