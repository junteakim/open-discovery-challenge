from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from meeting_copilot.llm import SMOOTH_FEEDBACK_SCHEMA, run_llm


def write_feedback_report(session: Path, config: dict[str, Any], context_dir: str | None) -> Path:
    transcript_path = session / "state" / "transcript.txt"
    if not transcript_path.is_file():
        live = session / "state" / "live_transcript.txt"
        transcript_path = live if live.is_file() else transcript_path

    transcript = transcript_path.read_text(encoding="utf-8") if transcript_path.is_file() else ""
    prompt = f"Full meeting transcript:\n{transcript}\n\n{SMOOTH_FEEDBACK_SCHEMA}"
    data = run_llm(prompt, config, context_dir)

    lines = [
        "# Meeting Feedback (Smooth-style)",
        "",
        "## Outcome",
        "",
        str(data.get("outcome", "")),
        "",
        "## Strengths",
    ]
    for s in data.get("strengths", []):
        lines.append(f"- {s}")
    lines.extend(["", "## Improvements"])
    for s in data.get("improvements", []):
        lines.append(f"- {s}")
    lines.extend(["", "## Sentence rewrites", ""])
    for row in data.get("sentences", []):
        if isinstance(row, dict):
            lines.append(f"**Original:** {row.get('original', '')}")
            lines.append(f"**Better:** {row.get('rewrite', '')}")
            lines.append(f"**Tip:** {row.get('tip', '')}")
            lines.append("")
    lines.extend(["## Expressions to learn", ""])
    for ex in data.get("expressions", []):
        if isinstance(ex, dict):
            lines.append(f"- **{ex.get('phrase', '')}** — {ex.get('meaning', '')}")
    lines.extend(["", "## Notes", "", str(data.get("notes", ""))])

    out = session / "feedback.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    (session / "feedback.json").write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return out
