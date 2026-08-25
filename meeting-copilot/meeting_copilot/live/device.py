from __future__ import annotations

from typing import Any, Tuple


def resolve_whisper_runtime(config: dict[str, Any]) -> Tuple[str, str, int]:
    """MacBook Air: force CPU int8 — no cloud, no CUDA probe latency."""
    live = config.get("live", {})
    profile = config.get("profile", "")
    device = live.get("whisper_device", "auto")
    compute = live.get("whisper_compute_type", "auto")
    threads = int(live.get("cpu_threads", 0))

    if profile == "macbook-air" or live.get("mode") == "lite":
        device, compute = "cpu", "int8"
        if threads <= 0:
            threads = 4

    if device == "auto":
        device = "cpu"
    if compute == "auto":
        compute = "int8" if device == "cpu" else "float16"
    if threads <= 0:
        threads = 4

    return str(device), str(compute), threads
