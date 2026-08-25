from __future__ import annotations

import re
from typing import Any

from meeting_copilot.ontology import extract_matched_terms, glossary_for_ui

# MeetU-style: 3 reply strategies (conservative / assertive / diplomatic)
REPLY_STRATEGIES: dict[str, dict[str, tuple[str, str]]] = {
    "default": {
        "conservative": (
            "That's a fair point. Let me think it through and follow up shortly.",
            "I'd like a moment to consider that carefully before I respond.",
        ),
        "assertive": (
            "Here's my take: we should move forward with a clear next step.",
            "I recommend we decide now and assign an owner today.",
        ),
        "diplomatic": (
            "I hear you. Maybe we can find a middle ground that works for both sides.",
            "Appreciate the perspective — let's align on a path that works for everyone.",
        ),
    },
    "timeline": {
        "conservative": (
            "On timing — I want to confirm dependencies before I commit.",
            "Let me double-check capacity and get back with a firm date.",
        ),
        "assertive": (
            "We can deliver by next Friday if scope stays as discussed.",
            "Next Friday works on our end — let's lock that in.",
        ),
        "diplomatic": (
            "If we prioritize the core items, next Friday is realistic; stretch goals may slip.",
            "We can hit the critical path by Friday and phase the rest.",
        ),
    },
    "budget": {
        "conservative": (
            "On budget — I'll share a range after I check with the team.",
            "I want to confirm numbers internally before I quote anything firm.",
        ),
        "assertive": (
            "The budget we had in mind is X; happy to walk through the breakdown.",
            "We're prepared to discuss pricing based on the scope we outlined.",
        ),
        "diplomatic": (
            "There's flexibility depending on scope — let's align on must-haves first.",
            "Happy to explore options that fit both budget and outcomes.",
        ),
    },
}

COMPOSE_TEMPLATES: dict[str, tuple[str, str]] = {
    "agree": (
        "I agree with that approach.",
        "Sounds good — I'm fully aligned with that direction.",
    ),
    "disagree": (
        "I see it a bit differently.",
        "I'd like to respectfully offer another perspective on this.",
    ),
    "question": (
        "Could you walk me through that in more detail?",
        "Just to make sure I follow — could you elaborate on that point?",
    ),
    "suggestion": (
        "One suggestion from our side would be the following.",
        "I'd like to propose an alternative we could explore together.",
    ),
}


def _topic_key(question: str) -> str:
    if re.search(r"timeline|deadline|when|schedule", question, re.I):
        return "timeline"
    if re.search(r"budget|cost|price|pricing", question, re.I):
        return "budget"
    return "default"


def heuristic_compose(mode: str, context_dir: str | None) -> tuple[str, str]:
    pair = COMPOSE_TEMPLATES.get(mode, COMPOSE_TEMPLATES["suggestion"])
    glossary = glossary_for_ui(context_dir)
    if glossary and mode == "suggestion":
        term = glossary[0]["term"]
        return pair[0], f"{pair[1]} Especially around {term}."
    return pair[0], pair[1]


def heuristic_reply(question: str, translated: str, context_dir: str | None) -> tuple[str, str]:
    """Backward-compatible: returns diplomatic as primary."""
    strategies = heuristic_reply_strategies(question, translated, context_dir)
    dip = strategies["diplomatic"]
    return dip[0], dip[1]


def heuristic_reply_strategies(
    question: str,
    translated: str,
    context_dir: str | None,
) -> dict[str, tuple[str, str]]:
    """MeetU-style three strategies — zero LLM cost."""
    topic = _topic_key(question)
    base = REPLY_STRATEGIES[topic]
    matched = extract_matched_terms(question, context_dir)
    out: dict[str, tuple[str, str]] = {}
    for key, (reply, native) in base.items():
        if matched:
            native = f"On {matched[0]} — {native}"
        out[key] = (reply, native)
    return out


def heuristic_brief(
    lines: list[str],
    context_dir: str | None = None,
    max_lines: int = 8,
) -> tuple[str, list[str]]:
    recent = [ln.strip() for ln in lines[-max_lines:] if ln.strip()]
    if not recent:
        return "Generating first summary…", []

    bullets = []
    for ln in recent[-5:]:
        short = ln[:100] + ("…" if len(ln) > 100 else "")
        bullets.append(f"• {short}")
    brief = "\n".join(bullets)

    highlights: list[str] = []
    combined = " ".join(recent)
    highlights.extend(extract_matched_terms(combined, context_dir))

    stop = {"that", "this", "with", "have", "from", "what", "when", "would", "could", "about", "there", "their"}
    for word in re.findall(r"[A-Za-z]{5,}", combined):
        if word.lower() not in stop and word not in highlights:
            highlights.append(word)
        if len(highlights) >= 8:
            break

    return brief, highlights[:8]
