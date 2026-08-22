from __future__ import annotations

import json
import queue
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

import numpy as np

SAMPLE_RATE = 16000


@dataclass
class LiveSegment:
    text: str
    translated: str
    lang: str
    target_lang: str
    partial: bool = False
    ts: float = field(default_factory=time.time)


class LivePipeline:
    """Mic → streaming STT → immediate translation for face-to-face use."""

    def __init__(
        self,
        config: dict[str, Any],
        *,
        lang_a: str,
        lang_b: str,
        whisper_model: str = "base",
        chunk_seconds: float = 1.2,
        device_index: int | None = None,
        on_segment: Callable[[LiveSegment], None] | None = None,
    ) -> None:
        from meeting_copilot.live.translate_fast import FastTranslator, resolve_lang

        self._config = config
        self._lang_a_whisper, _ = resolve_lang(lang_a)
        self._lang_b_whisper, _ = resolve_lang(lang_b)
        self._whisper_model_name = whisper_model
        self._chunk_seconds = chunk_seconds
        self._device_index = device_index
        self._on_segment = on_segment
        self._translator = FastTranslator(config)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._whisper = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _emit(self, seg: LiveSegment) -> None:
        if self._on_segment:
            self._on_segment(seg)

    def _target_for(self, detected: str) -> str:
        if detected == self._lang_a_whisper:
            return self._lang_b_whisper
        if detected == self._lang_b_whisper:
            return self._lang_a_whisper
        return self._lang_b_whisper

    def _run(self) -> None:
        try:
            import sounddevice as sd
            from faster_whisper import WhisperModel
        except ImportError as exc:
            raise ImportError(
                "Install live extras: pip install meeting-copilot[live]"
            ) from exc

        self._whisper = WhisperModel(
            self._whisper_model_name,
            device="cpu",
            compute_type="int8",
        )

        block = int(SAMPLE_RATE * 0.1)
        frames_per_chunk = int(SAMPLE_RATE * self._chunk_seconds)
        audio_q: queue.Queue[np.ndarray] = queue.Queue()

        def callback(indata, _frames, _time, status) -> None:
            if status:
                return
            audio_q.put(indata.copy().reshape(-1))

        stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="float32",
            blocksize=block,
            device=self._device_index,
            callback=callback,
        )

        buffer = np.array([], dtype=np.float32)
        last_partial = ""

        with stream:
            while not self._stop.is_set():
                try:
                    chunk = audio_q.get(timeout=0.2)
                except queue.Empty:
                    continue
                buffer = np.concatenate([buffer, chunk])
                if len(buffer) < frames_per_chunk:
                    continue

                window = buffer[:frames_per_chunk]
                buffer = buffer[frames_per_chunk // 2 :]

                rms = float(np.sqrt(np.mean(window**2)))
                if rms < 0.008:
                    continue

                segments, info = self._whisper.transcribe(
                    window,
                    beam_size=1,
                    best_of=1,
                    vad_filter=True,
                    language=None,
                )
                text = " ".join(s.text.strip() for s in segments).strip()
                if not text or text == last_partial:
                    continue

                detected = info.language or self._lang_a_whisper
                tgt = self._target_for(detected)
                translated = self._translator.translate(text, detected, tgt)

                seg = LiveSegment(
                    text=text,
                    translated=translated,
                    lang=detected,
                    target_lang=tgt,
                    partial=True,
                )
                self._emit(seg)
                last_partial = text

                final = LiveSegment(
                    text=text,
                    translated=translated,
                    lang=detected,
                    target_lang=tgt,
                    partial=False,
                )
                self._emit(final)
                last_partial = ""
