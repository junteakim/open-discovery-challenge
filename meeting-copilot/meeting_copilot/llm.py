from __future__ import annotations

import json
import re
import subprocess
from typing import Any

from meeting_copilot.config import build_context_block


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "questions": [],
            "topics": [],
            "decisions": [],
            "risks": [],
            "followups": [],
            "translation_lines": [],
            "briefing_summary": text[:2000],
        }


def run_llm(
    prompt: str,
    config: dict[str, Any],
    context_dir: str | None = None,
) -> dict[str, Any]:
    llm = config.get("llm", {})
    provider = llm.get("provider", "echo")
    context = build_context_block()
    if context_dir:
        from pathlib import Path

        context = build_context_block(Path(context_dir))

    full_prompt = f"{context}\n\n---\n\n{prompt}"

    if provider == "echo":
        return _extract_json(
            '{"questions":["Review ontology-backed talking points"],'
            '"topics":[],"decisions":[],"risks":[],"followups":[],'
            '"translation_lines":[]}'
        )

    section = llm.get(provider, {})
    command = section.get("command", [])
    if not command:
        raise ValueError(f"No CLI command configured for provider '{provider}'")

    env_extra = section.get("env", {})
    result = subprocess.run(
        command,
        input=full_prompt,
        capture_output=True,
        text=True,
        env=None,
        check=False,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip() or "LLM CLI failed"
        raise RuntimeError(stderr)
    return _extract_json(result.stdout)


UPDATE_SCHEMA = """
Respond with a single JSON object (no markdown outside the JSON) with keys:
- questions: string[] (3-6 ranked suggestions, questions to ask now)
- topics: string[] (topic status lines, e.g. "✓ Budget discussed")
- decisions: string[]
- risks: string[]
- followups: string[] (action items with owner if known)
- translation_lines: string[] (optional translated lines for display)

Focus only on NEW transcript delta. Use ontology entities and memory when relevant.
"""


CREATE_SCHEMA = """
Respond with a single JSON object with keys:
- goal: string
- participants: string[]
- constraints: string[]
- planned_topics: string[]
- opening_questions: string[] (grouped by theme in strings)
- briefing_summary: string (TL;DR for dashboard)
"""


CLOSE_SCHEMA = """
Respond with a single JSON object with keys:
- outcome: string
- decisions: string[]
- action_items: array of {item, owner, due, status}
- open_questions: string[]
- followup_draft: string (email/message draft)
"""
