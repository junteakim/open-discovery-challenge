from __future__ import annotations

import re
from typing import Any

from meeting_copilot.config import load_ontology

# Zero-cost English phrase chips (no LLM)
COMPOSE_TEMPLATES: dict[str, tuple[str, str]] = {
    "agree": (
        "I agree with that.",
        "Sounds good — I'm aligned with that.",
    ),
    "disagree": (
        "I see it differently.",
        "I'd like to offer a different perspective.",
    ),
    "question": (
        "Could you clarify that point?",
        "Just to confirm — could you elaborate on that?",
    ),
    "suggestion": (
        "One suggestion from our side:",
        "I'd like to propose the following:",
    ),
}

QUESTION_REPLY_TEMPLATES: list[tuple[str, str]] = [
    (
        "Let me address that directly.",
        "Good question — let me walk through that.",
    ),
    (
        "I'll need a moment to think about that.",
        "That's a fair point. Here's how I see it.",
    ),
    (
        "Can I follow up on that after this call?",
        "Let me circle back to that in a moment.",
    ),
]


def _ontology_terms(context_dir: str | None) -> list[str]:
    from pathlib import Path

    raw = load_ontology(Path(context_dir) if context_dir else None)
    terms = raw.get("terms") or {}
    out: list[str] = list(terms.keys())
    for ent in raw.get("entities") or []:
        if isinstance(ent, dict):
            labels = ent.get("labels", {})
            if isinstance(labels, dict):
                out.extend(labels.values())
    return out


def heuristic_compose(mode: str, context_dir: str | None) -> tuple[str, str]:
    pair = COMPOSE_TEMPLATES.get(mode, COMPOSE_TEMPLATES["suggestion"])
    terms = _ontology_terms(context_dir)
    hint = f" (context: {terms[0]})" if terms else ""
    return pair[0], pair[1] + hint


def heuristic_reply(question: str, translated: str, context_dir: str | None) -> tuple[str, str]:
    idx = len(question) % len(QUESTION_REPLY_TEMPLATES)
    reply, native = QUESTION_REPLY_TEMPLATES[idx]
    terms = _ontology_terms(context_dir)
    for term in terms:
        if term.lower() in question.lower():
            native = f"Regarding {term} — {native}"
            break
    if translated and translated != question:
        reply = f"{reply} ({translated})"
    return reply, native


def heuristic_brief(lines: list[str], max_lines: int = 10) -> tuple[str, list[str]]:
    recent = [ln.strip() for ln in lines[-max_lines:] if ln.strip()]
    if not recent:
        return "Listening…", []
    brief = "\n".join(f"• {ln[:120]}" for ln in recent)
    highlights: list[str] = []
    for ln in recent[-3:]:
        for word in re.findall(r"[A-Za-z]{4,}", ln):
            if word.lower() not in {"that", "this", "with", "have", "from", "what", "when"}:
                highlights.append(word)
    return brief, highlights[:6]
