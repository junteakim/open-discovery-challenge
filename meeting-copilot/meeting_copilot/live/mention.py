from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


@dataclass
class MentionHit:
    kind: str  # name | question | request
    matched: str


def detect_mention(
    text: str,
    *,
    names: Iterable[str] | None = None,
) -> MentionHit | None:
    """MeetU-style: alert when someone addresses you or asks a question."""
    t = text.strip()
    if not t:
        return None

    names = list(names or [])
    lower = t.lower()
    for name in names:
        if name and name.lower() in lower:
            return MentionHit(kind="name", matched=name)

    if "?" in t or re.search(
        r"^(what|why|how|when|where|who|could you|can you|would you|do you)\b",
        t,
        re.I,
    ):
        return MentionHit(kind="question", matched="?")

    if re.search(r"\b(please|could you|can we|let'?s)\b", t, re.I):
        return MentionHit(kind="request", matched="request")

    return None
