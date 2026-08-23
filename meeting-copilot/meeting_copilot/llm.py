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
        return {"raw": text[:4000]}


def _full_prompt(prompt: str, config: dict[str, Any], context_dir: str | None) -> str:
    context = build_context_block()
    if context_dir:
        from pathlib import Path

        context = build_context_block(Path(context_dir))
    return f"{context}\n\n---\n\n{prompt}"


def run_llm_raw(prompt: str, config: dict[str, Any], context_dir: str | None = None) -> str:
    llm = config.get("llm", {})
    provider = llm.get("provider", "echo")
    full_prompt = _full_prompt(prompt, config, context_dir)

    if provider == "echo":
        return _echo_response(prompt)

    section = llm.get(provider, {})
    command = section.get("command", [])
    if not command:
        raise ValueError(f"No CLI command configured for provider '{provider}'")

    result = subprocess.run(
        command,
        input=full_prompt,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "LLM CLI failed")
    return result.stdout.strip()


def run_llm(
    prompt: str,
    config: dict[str, Any],
    context_dir: str | None = None,
) -> dict[str, Any]:
    raw = run_llm_raw(prompt, config, context_dir)
    parsed = _extract_json(raw)
    if "raw" in parsed and len(parsed) == 1:
        return _extract_json(raw) if raw.startswith("{") else {
            "questions": [],
            "topics": [],
            "decisions": [],
            "risks": [],
            "followups": [],
            "translation_lines": [],
            "briefing_summary": raw[:2000],
        }
    return parsed


def _echo_response(prompt: str) -> str:
    lower = prompt.lower()
    if "compose" in lower or "agree" in lower or "disagree" in lower:
        return json.dumps(
            {
                "reply": "That makes sense. I agree with that direction and we can move forward.",
                "reply_native": "Sounds good — I'm aligned with that approach.",
            },
            ensure_ascii=False,
        )
    if "question" in lower and "detect" not in lower:
        return json.dumps(
            {
                "reply": "Could you clarify the timeline and who owns the next step?",
                "reply_native": "Just to confirm — what's the timeline, and who's driving this?",
            },
            ensure_ascii=False,
        )
    if "brief" in lower or "summary" in lower:
        return json.dumps(
            {
                "brief": "• Discussing project scope and timeline\n• Open: budget approval\n• Next: share proposal by Friday",
                "highlights": ["scope", "timeline", "budget"],
            },
            ensure_ascii=False,
        )
    if "feedback" in lower or "rewrite" in lower:
        return json.dumps(
            {
                "outcome": "Productive alignment on scope.",
                "sentences": [
                    {
                        "original": "I think we can do that maybe next week.",
                        "rewrite": "We can deliver that by next Friday.",
                        "tip": "Use a concrete date instead of 'maybe'.",
                    }
                ],
                "expressions": [
                    {"phrase": "move forward", "meaning": "proceed with a plan"}
                ],
                "strengths": ["Clear intent"],
                "improvements": ["More specific commitments"],
            },
            ensure_ascii=False,
        )
    return json.dumps(
        {
            "reply": "Thanks for sharing. Let me add one point from our side.",
            "reply_native": "Got it — I'd like to add a quick thought on our end.",
        },
        ensure_ascii=False,
    )


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


SMOOTH_BRIEF_SCHEMA = """
Respond JSON only:
{"brief": "bullet summary (max 6 lines)", "highlights": ["key terms to watch"]}
Use ontology/memory when relevant. Meeting is in progress — be concise.
"""


SMOOTH_REPLY_SCHEMA = """
Respond JSON only. User is a non-native English speaker in a live meeting.
{"reply": "ready-to-say English reply (1-3 sentences)", "reply_native": "same meaning, more natural/native phrasing"}
Be concise, professional, and sayable aloud immediately.
"""


SMOOTH_COMPOSE_SCHEMA = """
Respond JSON only. Mode: {mode}. Last utterance: "{utterance}"
{"reply": "ready-to-say English", "reply_native": "more natural alternative"}
Modes: agree | disagree | question | suggestion
"""


SMOOTH_FEEDBACK_SCHEMA = """
Respond JSON only — post-meeting English coaching (Smooth AI style):
{
  "outcome": "one paragraph",
  "sentences": [{"original": "...", "rewrite": "...", "tip": "..."}],
  "expressions": [{"phrase": "...", "meaning": "..."}],
  "strengths": ["..."],
  "improvements": ["..."],
  "notes": "structured meeting notes markdown"
}
"""
