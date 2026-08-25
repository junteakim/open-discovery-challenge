from __future__ import annotations

import re
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable

from meeting_copilot.llm import (
    SMOOTH_BRIEF_SCHEMA,
    SMOOTH_COMPOSE_SCHEMA,
    SMOOTH_REPLY_SCHEMA,
    run_llm,
)
from meeting_copilot.live.lite_copilot import (
    heuristic_brief,
    heuristic_compose,
    heuristic_reply_strategies,
)
from meeting_copilot.live.mention import detect_mention

QUESTION_RE = re.compile(
    r"(\?|^(could|can|would|will|what|why|how|when|where|who|do you|did you|is there|are we)\b)",
    re.I,
)


def looks_like_question(text: str) -> bool:
    t = text.strip()
    if not t:
        return False
    if "?" in t:
        return True
    return bool(QUESTION_RE.search(t))


@dataclass
class CopilotState:
    transcript_lines: list[str] = field(default_factory=list)
    brief: str = "Listening…"
    highlights: list[str] = field(default_factory=list)
    last_suggestion: str = ""
    last_suggestion_native: str = ""
    last_compose: str = ""


class CopilotBrain:
    """Live brief + suggestions. Lite mode = zero LLM cost (MacBook Air)."""

    def __init__(
        self,
        config: dict[str, Any],
        *,
        context_dir: str | None = None,
        on_event: Callable[[dict[str, Any]], None] | None = None,
        brief_every_n: int | None = None,
    ) -> None:
        live = config.get("live", {})
        self._lite = live.get("mode", "lite") == "lite"
        self._config = config
        self._context_dir = context_dir
        self._on_event = on_event
        self._state = CopilotState()
        self._brief_every_n = max(
            1,
            brief_every_n or int(live.get("brief_every_n", 5 if self._lite else 3)),
        )
        self._my_names = [str(n) for n in live.get("my_names", []) if n]
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=1)
        self._segment_count = 0

    @property
    def state(self) -> CopilotState:
        return self._state

    @property
    def lite(self) -> bool:
        return self._lite

    def transcript_text(self) -> str:
        with self._lock:
            return "\n".join(self._state.transcript_lines)

    def _emit(self, event: dict[str, Any]) -> None:
        if self._on_event:
            self._on_event(event)

    def on_final_segment(self, text: str, translated: str, lang: str) -> None:
        with self._lock:
            self._state.transcript_lines.append(text)
            self._segment_count += 1
            count = self._segment_count

        if looks_like_question(text):
            self._pool.submit(self._suggest_reply, text, translated)

        mention = detect_mention(text, names=self._my_names)
        if mention:
            self._emit(
                {
                    "type": "mention",
                    "kind": mention.kind,
                    "matched": mention.matched,
                    "text": text,
                }
            )

        if count == 1 or count % self._brief_every_n == 0:
            self._pool.submit(self._update_brief)

    def compose(self, mode: str, utterance: str | None = None) -> None:
        self._pool.submit(self._compose, mode, utterance)

    def _suggest_reply(self, question: str, translated: str) -> None:
        if self._lite:
            strategies = heuristic_reply_strategies(question, translated, self._context_dir)
            reply, native = strategies["diplomatic"]
            payload = {
                "type": "suggestion",
                "question": question,
                "reply": reply,
                "reply_native": native,
                "strategies": {
                    k: {"reply": v[0], "reply_native": v[1]} for k, v in strategies.items()
                },
            }
            with self._lock:
                self._state.last_suggestion = reply
                self._state.last_suggestion_native = native
            self._emit(payload)
            return

        prompt = (
            f"A meeting participant asked or said:\n{question}\n\n"
            f"Translation hint: {translated}\n\n"
            f"Recent transcript:\n{self.transcript_text()[-3000:]}\n\n"
            f"{SMOOTH_REPLY_SCHEMA}"
        )
        try:
            data = run_llm(prompt, self._config, self._context_dir)
            reply = data.get("reply") or data.get("raw", "")
            native = data.get("reply_native", reply)
        except Exception as exc:
            reply = f"(LLM unavailable: {exc})"
            native = reply

        with self._lock:
            self._state.last_suggestion = reply
            self._state.last_suggestion_native = native

        self._emit(
            {
                "type": "suggestion",
                "question": question,
                "reply": reply,
                "reply_native": native,
            }
        )

    def _update_brief(self) -> None:
        if self._lite:
            with self._lock:
                lines = list(self._state.transcript_lines)
            brief, highlights = heuristic_brief(lines, self._context_dir)
        else:
            prompt = (
                f"Live meeting transcript so far:\n{self.transcript_text()[-6000:]}\n\n"
                f"{SMOOTH_BRIEF_SCHEMA}"
            )
            try:
                data = run_llm(prompt, self._config, self._context_dir)
                brief = data.get("brief", "")
                highlights = data.get("highlights", [])
            except Exception as exc:
                brief = f"(Brief unavailable: {exc})"
                highlights = []

        with self._lock:
            self._state.brief = brief or self._state.brief
            if highlights:
                self._state.highlights = highlights

        self._emit({"type": "brief", "brief": brief, "highlights": highlights})

    def _compose(self, mode: str, utterance: str | None) -> None:
        if self._lite:
            reply, native = heuristic_compose(mode, self._context_dir)
        else:
            last = utterance or (
                self._state.transcript_lines[-1] if self._state.transcript_lines else ""
            )
            schema = SMOOTH_COMPOSE_SCHEMA.format(mode=mode, utterance=last[:500])
            prompt = f"{schema}\n\nTranscript tail:\n{self.transcript_text()[-2000:]}"
            try:
                data = run_llm(prompt, self._config, self._context_dir)
                reply = data.get("reply", "")
                native = data.get("reply_native", reply)
            except Exception as exc:
                reply = f"(Compose failed: {exc})"
                native = reply

        with self._lock:
            self._state.last_compose = reply

        self._emit(
            {
                "type": "compose",
                "mode": mode,
                "reply": reply,
                "reply_native": native,
            }
        )

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)
