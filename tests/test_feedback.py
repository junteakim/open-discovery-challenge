"""Feedback jsonl persistence tests (rule 6)."""

import json
import tempfile
from pathlib import Path

from discovery.feedback.store import FeedbackEntry, FeedbackStore


def test_feedback_jsonl_write_and_load():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "feedback.jsonl"
        store = FeedbackStore(path)
        entry = FeedbackEntry(
            smiles="CCO",
            axes={"activity": 10.0},
            total=65.0,
            lower_bound=60.0,
            uncertainty=5.0,
            gate_failures=[],
            gate_passed=True,
            generation=1,
            family="benzimidazole_amide",
        )
        store.append(entry)
        store.append(
            FeedbackEntry(
                smiles="CCN",
                total=70.0,
                family="quinazoline_urea",
                gate_passed=True,
            )
        )

        rows = store.load_all()
        assert len(rows) == 2
        assert rows[0]["smiles"] == "CCO"
        assert rows[0]["axes"]["activity"] == 10.0
        assert rows[0]["lower_bound"] == 60.0
        assert rows[0]["family"] == "benzimidazole_amide"
        assert "timestamp" in rows[0]

        # Valid jsonl
        raw = path.read_text().strip().splitlines()
        for line in raw:
            json.loads(line)

        index = store.load_index()
        assert "CCO" in index
        assert index["CCO"]["total"] == 65.0
