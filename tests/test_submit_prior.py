"""Tests for submit blocking with MW-band prior."""

import tempfile
from pathlib import Path

from discovery.cli import cmd_submit
from discovery.config import Config


def test_submit_dry_run_rejects_low_prior(monkeypatch):
    """Submit dry-run should refuse low prior even without replay cache."""
    import argparse
    
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        cfg = Config.from_env(root)
        cfg.paths.feedback.parent.mkdir(parents=True, exist_ok=True)
        
        # Small amide seed ~135 Da — should be blocked by prior
        args = argparse.Namespace(
            structure="CC(=O)Nc1ccccc1",  # acetanilide
            display_name="TestSmallMolecule",
            model_name="",
            rationale="",
            visibility="private",
            family="",
            dry_run=True,
            root=root,
        )
        
        # Mock FinalBenchProvider.available() to return True
        def mock_available(self):
            return True
        
        from discovery.providers import finalbench
        monkeypatch.setattr(finalbench.FinalBenchProvider, "available", mock_available)
        
        exit_code = cmd_submit(args)
        
        # Should be rejected (exit code 4) due to low prior
        assert exit_code == 4, f"Expected exit code 4 (prior rejection), got {exit_code}"


def test_submit_dry_run_rejects_450da_molecule(monkeypatch):
    """Submit dry-run should reject 450 Da molecules (median 42.6 in 450-500 band)."""
    import argparse
    
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        cfg = Config.from_env(root)
        cfg.paths.feedback.parent.mkdir(parents=True, exist_ok=True)
        
        # Molecule in 450-500 band (~451 Da) - median 42.6, should FAIL
        args = argparse.Namespace(
            structure="c1ccc2[nH]c(C(=O)NCCOC)nc2c1c1ccc(OC)c(c1)c1ccc2ccccc2c1",
            display_name="Test450Da",
            model_name="",
            rationale="",
            visibility="private",
            family="",
            dry_run=True,
            root=root,
        )
        
        # Mock FinalBenchProvider.available() to return True
        def mock_available(self):
            return True
        
        from discovery.providers import finalbench
        monkeypatch.setattr(finalbench.FinalBenchProvider, "available", mock_available)
        
        exit_code = cmd_submit(args)
        
        # Should be rejected (exit code 4) - median 42.6 ≤ 60
        assert exit_code == 4, f"Expected exit code 4 (prior rejection for 450-500 band), got {exit_code}"


def test_submit_dry_run_accepts_500_550_band(monkeypatch):
    """Submit dry-run should accept 500-550 band molecules (median 67.6 >60)."""
    import argparse
    
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        cfg = Config.from_env(root)
        cfg.paths.feedback.parent.mkdir(parents=True, exist_ok=True)
        
        # Molecule in 500-550 band (~512 Da) - median 67.6, should PASS
        args = argparse.Namespace(
            structure="c1ccc2[nH]c(C(=O)NCCc3ccccc3)nc2c1c1ccc(OC)c(C)c1c1ccc2ccccc2c1",
            display_name="Test512Da",
            model_name="",
            rationale="",
            visibility="private",
            family="",
            dry_run=True,
            root=root,
        )
        
        # Mock FinalBenchProvider.available() to return True
        def mock_available(self):
            return True
        
        from discovery.providers import finalbench
        monkeypatch.setattr(finalbench.FinalBenchProvider, "available", mock_available)
        
        exit_code = cmd_submit(args)
        
        # Should pass (exit code 0) - median 67.6 > 60
        assert exit_code == 0, f"Expected exit code 0 (success), got {exit_code}"
