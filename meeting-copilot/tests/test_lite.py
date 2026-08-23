from meeting_copilot.config import apply_profile, load_config
from meeting_copilot.live.lite_copilot import heuristic_brief, heuristic_reply
from meeting_copilot.live.copilot_engine import CopilotBrain


def test_macbook_air_profile():
    cfg = apply_profile({"profiles": {"macbook-air": {"live": {"mode": "lite"}}}}, "macbook-air")
    assert cfg["live"]["mode"] == "lite"


def test_heuristic_reply_no_llm():
    reply, native = heuristic_reply("What is the timeline?", "일정이 어떻게 되나요?", None)
    assert reply
    assert native


def test_heuristic_brief():
    brief, hl = heuristic_brief(["Hello team", "We discussed budget"])
    assert "budget" in brief.lower() or "Hello" in brief


def test_copilot_brain_lite_no_api():
    brain = CopilotBrain({"live": {"mode": "lite"}})
    assert brain.lite
    events = []
    brain._on_event = events.append
    brain.on_final_segment("What do you think?", "어떻게 생각하세요?", "en")
    brain._pool.shutdown(wait=True)
    assert any(e.get("type") == "suggestion" for e in events) or brain.state.last_suggestion
