from meeting_copilot.feedback import write_feedback_report


def test_feedback_report(tmp_path, monkeypatch):
    session = tmp_path / "sess"
    state = session / "state"
    state.mkdir(parents=True)
    (state / "live_transcript.txt").write_text("[en] Hello, I think we can do that maybe next week.")

    config = {"llm": {"provider": "echo"}}
    out = write_feedback_report(session, config, None)
    assert out.is_file()
    text = out.read_text(encoding="utf-8")
    assert "Feedback" in text or "feedback" in text.lower()
