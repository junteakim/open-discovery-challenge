from pathlib import Path

from meeting_copilot.diff import transcript_delta
from meeting_copilot.config import build_context_block
from meeting_copilot.session import slugify, create_session, apply_update


def test_transcript_delta_prefix():
    old = "Hello world"
    new = "Hello world. More text."
    assert transcript_delta(old, new) == ". More text."


def test_slugify():
    assert slugify("Discovery with Company X!") == "discovery-with-company-x"


def test_context_block_includes_memory(tmp_path: Path):
    ctx = tmp_path
    (ctx / "ontology.json").write_text('{"entities":[]}')
    (ctx / "memory.md").write_text("Remember the budget thread.")
    block = build_context_block(ctx)
    assert "ontology" in block.lower() or "entities" in block
    assert "budget" in block


def test_create_and_update_echo(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from meeting_copilot.session import SESSIONS_ROOT

    # Redirect sessions to tmp
    import meeting_copilot.session as sm

    sm.SESSIONS_ROOT = tmp_path / "sessions"

    root = create_session(
        "Test Meeting",
        "discovery",
        ["Alice"],
        {
            "goal": "Test goal",
            "briefing_summary": "TLDR",
            "planned_topics": ["Intro"],
            "opening_questions": ["What is the timeline?"],
            "constraints": [],
            "participants": ["Alice"],
        },
    )
    assert root.is_dir()
    apply_update(
        root,
        {
            "questions": ["Ask about budget"],
            "topics": ["✓ Intro discussed"],
            "decisions": [],
            "risks": ["Timeline slip"],
            "followups": ["Send follow-up email"],
        },
    )
    q = (root / "app" / "tabs" / "questions.js").read_text()
    assert "budget" in q.lower()
