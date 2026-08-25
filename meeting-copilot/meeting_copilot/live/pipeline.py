from __future__ import annotations

import queue
import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np

from meeting_copilot.live.device import resolve_whisper_runtime
from meeting_copilot.live.hallucinations import looks_like_hallucination

SAMPLE_RATE = 16000


@dataclass
class LiveSegment:
    text: str
    translated: str
    lang: str
    target_lang: str
    partial: bool = False
    ts: float = field(default_factory=lambda: __import__("time").time())


class LivePipeline:
    """Mic → streaming STT → Marian translation. Optimized for MacBook Air CPU."""

    def __init__(
        self,
        config: dict[str, Any],
        *,
        lang_a: str,
        lang_b: str,
        whisper_model: str | None = None,
        chunk_seconds: float | None = None,
        device_index: int | None = None,
        on_segment: Callable[[LiveSegment], None] | None = None,
    ) -> None:
        from meeting_copilot.live.translate_fast import FastTranslator, resolve_lang

        live_cfg = config.get("live", {})
        self._config = config
        self._lite = live_cfg.get("mode", "lite") == "lite"
        self._lang_a_whisper, _ = resolve_lang(lang_a)
        self._lang_b_whisper, _ = resolve_lang(lang_b)
        self._whisper_model_name = whisper_model or live_cfg.get("whisper_model", "tiny")
        default_chunk = 0.65 if self._lite else 0.85
        self._chunk_seconds = chunk_seconds or float(live_cfg.get("chunk_seconds", default_chunk))
        self._device_index = device_index
        self._on_segment = on_segment
        self._translator = FastTranslator(config)
        self._stop = threading.Event()
        self._ready = threading.Event()
        self._thread: threading.Thread | None = None
        self._whisper = None
        self._translate_pool = ThreadPoolExecutor(max_workers=1)

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def wait_ready(self, timeout: float = 120.0) -> bool:
        return self._ready.wait(timeout=timeout)

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)
        self._translate_pool.shutdown(wait=False, cancel_futures=True)

    def _emit(self, seg: LiveSegment) -> None:
        if self._on_segment:
            self._on_segment(seg)

    def _target_for(self, detected: str) -> str:
        if detected == self._lang_a_whisper:
            return self._lang_b_whisper
        if detected == self._lang_b_whisper:
            return self._lang_a_whisper
        return self._lang_b_whisper

    def _maybe_translate(self, text: str, detected: str, tgt: str) -> str:
        if detected == tgt:
            return text
        words = text.split()
        if self._lite and len(words) < 2:
            return text
        return self._translator.translate(text, detected, tgt)

    def _run(self) -> None:
        try:
            import sounddevice as sd
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise ImportError(
                "Install live extras: pip install meeting-copilot[live]"
            ) from exc

        device, compute, cpu_threads = resolve_whisper_runtime(self._config)
        self._whisper = WhisperModel(
            self._whisper_model_name,
            device=device,
            compute_type=compute,
            cpu_threads=cpu_threads,
        )

        frames_per_chunk = int(SAMPLE_RATE * self._chunk_seconds)
        # Warm-up — first real utterance is faster
        silent = np.zeros(frames_per_chunk, dtype=np.float32)
        self._whisper.transcribe(
            silent,
            beam_size=1,
            vad_filter=False,
            language=None,
            condition_on_previous_text=False,
        )
        self._ready.set()

        block = int(SAMPLE_RATE * 0.05)
        audio_q: queue.Queue[np.ndarray] = queue.Queue(maxsize=32)

        def callback(indata, _frames, _time, status) -> None:
            if status:
                return
            try:
                audio_q.put_nowait(indata.copy().reshape(-1))
            except queue.Full:
                try:
                    audio_q.get_nowait()
                except queue.Empty:
                    pass
                audio_q.put_nowait(indata.copy().reshape(-1))

        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=block,
            device=self._device_index,
            callback=callback,
        )

        buffer = np.array([], dtype=np.float32)
        last_text = ""
        hop = max(1, frames_per_chunk // 3)

        with stream:
            while not self._stop.is_set():
                try:
                    chunk = audio_q.get(timeout=0.1)
                except queue.Empty:
                    continue
                buffer = np.concatenate([buffer, chunk])
                if len(buffer) < frames_per_chunk:
                    continue

                window = buffer[:frames_per_chunk]
                buffer = buffer[hop:]

                rms = float(np.sqrt(np.mean(window**2)))
                if rms < 0.005:
                    continue

                segments, info = self._whisper.transcribe(
                    window,
                    beam_size=1,
                    best_of=1,
                    vad_filter=not self._lite,
                    language=None,
                    condition_on_previous_text=False,
                    temperature=0.0,
                    without_timestamps=True,
                )
                text = " ".join(s.text.strip() for s in segments).strip()
                if not text or text == last_text:
                    continue
                if looks_like_hallucination(text):
                    continue

                detected = info.language or self._lang_a_whisper
                tgt = self._target_for(detected)
                last_text = text

                # Show STT immediately (lower perceived latency)
                self._emit(
                    LiveSegment(
                        text=text,
                        translated="…",
                        lang=detected,
                        target_lang=tgt,
                        partial=True,
                    )
                )

                translated = self._translate_pool.submit(
                    self._maybe_translate, text, detected, tgt
                ).result()

                self._emit(
                    LiveSegment(
                        text=text,
                        translated=translated,
                        lang=detected,
                        target_lang=tgt,
                        partial=False,
                    )
                )
                last_text = ""
