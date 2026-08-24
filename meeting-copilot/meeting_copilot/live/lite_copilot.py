from __future__ import annotations

import re
from typing import Any

from meeting_copilot.ontology import extract_matched_terms, glossary_for_ui

# Natural English phrase chips — Smooth-style ready-to-say lines
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

QUESTION_PATTERNS: list[tuple[re.Pattern[str], tuple[str, str]]] = [
    (re.compile(r"timeline|deadline|when", re.I), (
        "Regarding the timeline — we can target next Friday if that works.",
        "On timing — I think next Friday is realistic on our end.",
    )),
    (re.compile(r"budget|cost|price", re.I), (
        "On budget — let me share what we had in mind.",
        "Happy to walk through the numbers with you.",
    )),
    (re.compile(r"why|reason", re.I), (
        "The main reason is we want to reduce risk before scaling.",
        "Primarily, we're trying to de-risk before we commit further.",
    )),
    (re.compile(r"how|process", re.I), (
        "Here's how we'd approach it step by step.",
        "Let me outline the process we'd follow.",
    )),
]

QUESTION_REPLY_DEFAULT: tuple[str, str] = (
    "That's a great question — let me address it directly.",
    "Good question. Here's how I see it.",
)


def heuristic_compose(mode: str, context_dir: str | None) -> tuple[str, str]:
    pair = COMPOSE_TEMPLATES.get(mode, COMPOSE_TEMPLATES["suggestion"])
    glossary = glossary_for_ui(context_dir)
    if glossary and mode == "suggestion":
        term = glossary[0]["term"]
        return pair[0], f"{pair[1]} Especially around {term}."
    return pair[0], pair[1]


def heuristic_reply(question: str, translated: str, context_dir: str | None) -> tuple[str, str]:
    for pattern, pair in QUESTION_PATTERNS:
        if pattern.search(question):
            reply, native = pair
            break
    else:
        reply, native = QUESTION_REPLY_DEFAULT

    matched = extract_matched_terms(question, context_dir)
    if matched:
        native = f"On {matched[0]} — {native}"

    return reply, native


def heuristic_brief(
    lines: list[str],
    context_dir: str | None = None,
    max_lines: int = 8,
) -> tuple[str, list[str]]:
    recent = [ln.strip() for ln in lines[-max_lines:] if ln.strip()]
    if not recent:
        return "Generating first summary…", []

    # Smooth-style bullet summary (not raw dump)
    bullets: list[str] = []
    for ln in recent[-5:]:
        short = ln[:100] + ("…" if len(ln) > 100 else "")
        bullets.append(f"• {short}")

    brief = "\n".join(bullets)

    # Highlights: ontology matches first, then frequent English words
    highlights: list[str] = []
    combined = " ".join(recent)
    highlights.extend(extract_matched_terms(combined, context_dir))

    stop = {"that", "this", "with", "have", "from", "what", "when", "would", "could", "about", "there", "their"}
    for word in re.findall(r"[A-Za-z]{5,}", combined):
        w = word.lower()
        if w not in stop and word not in highlights:
            highlights.append(word)
        if len(highlights) >= 8:
            break

    return brief, highlights[:8]
