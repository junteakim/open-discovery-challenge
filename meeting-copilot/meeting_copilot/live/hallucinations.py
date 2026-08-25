from __future__ import annotations

import re

# Whisper silence / YouTube-style hallucinations (MeetU pattern)
HALLUCINATION_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"^thank you for watching\.?$", re.I),
    re.compile(r"^thanks for watching\.?$", re.I),
    re.compile(r"^please subscribe\.?$", re.I),
    re.compile(r"^subscribe to (my|the) channel\.?$", re.I),
    re.compile(r"^자막\s*제공", re.I),
    re.compile(r"^MBC\s*뉴스", re.I),
    re.compile(r"^시청해\s*주셔서", re.I),
    re.compile(r"^♪+$"),
    re.compile(r"^\[?\s*(music|silence|applause)\s*\]?$", re.I),
    re.compile(r"^(uh+|um+|ah+)\.?$", re.I),
]


def looks_like_hallucination(text: str) -> bool:
    t = text.strip()
    if not t:
        return True
    if len(t) <= 1:
        return True
    for pat in HALLUCINATION_PATTERNS:
        if pat.match(t):
            return True
    # Repeated single token (e.g. "you you you you")
    parts = t.lower().split()
    if len(parts) >= 4 and len(set(parts)) == 1:
        return True
    return False
