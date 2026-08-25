from meeting_copilot.live.hallucinations import looks_like_hallucination
from meeting_copilot.live.mention import detect_mention
from meeting_copilot.live.lite_copilot import heuristic_reply_strategies


def test_hallucination_filter():
    assert looks_like_hallucination("Thank you for watching.")
    assert looks_like_hallucination("you you you you")
    assert not looks_like_hallucination("What's the timeline for launch?")


def test_mention_detection():
    hit = detect_mention("Alex, can you share the update?", names=["Alex"])
    assert hit is not None
    assert hit.kind == "name"
    q = detect_mention("What do you think about the plan?")
    assert q is not None
    assert q.kind == "question"


def test_three_strategies():
    s = heuristic_reply_strategies("What's the timeline?", "", None)
    assert set(s.keys()) == {"conservative", "assertive", "diplomatic"}
