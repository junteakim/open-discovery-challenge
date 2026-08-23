from __future__ import annotations

from typing import Any, Tuple


def resolve_whisper_runtime(config: dict[str, Any]) -> Tuple[str, str]:
    """Return (device, compute_type) for faster-whisper."""
    live = config.get("live", {})
    device = live.get("whisper_device", "auto")
    compute = live.get("whisper_compute_type", "auto")

    if device == "auto":
        try:
            import torch

            if torch.cuda.is_available():
                device = "cuda"
            else:
                device = "cpu"
        except ImportError:
            device = "cpu"

    if compute == "auto":
        compute = "float16" if device == "cuda" else "int8"

    return str(device), str(compute)
