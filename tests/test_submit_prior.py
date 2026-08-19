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


def test_submit_dry_run_accepts_competitive_mw(monkeypatch):
    """Submit dry-run should accept molecules in competitive MW band with prior >60."""
    import argparse
    
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        cfg = Config.from_env(root)
        cfg.paths.feedback.parent.mkdir(parents=True, exist_ok=True)
        
        # Molecule in competitive range (~451 Da)
        args = argparse.Namespace(
            structure="c1ccc2[nH]c(C(=O)NCCOC)nc2c1c1ccc(OC)c(c1)c1ccc2ccccc2c1",
            display_name="TestCompetitiveMW",
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
        
        # Should pass (exit code 0)
        assert exit_code == 0, f"Expected exit code 0 (success), got {exit_code}"
