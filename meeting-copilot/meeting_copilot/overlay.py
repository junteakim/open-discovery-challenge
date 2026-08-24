from __future__ import annotations

import threading
import time
from typing import Callable


def open_overlay_window(
    url: str,
    *,
    width: int = 420,
    height: int = 740,
    on_top: bool = True,
    transparent: bool = False,
) -> None:
    try:
        import webview
    except ImportError as exc:
        raise ImportError(
            "Install overlay extras: pip install meeting-copilot[overlay]"
        ) from exc

    window = webview.create_window(
        "Flow — Meeting Copilot",
        url,
        width=width,
        height=height,
        on_top=on_top,
        transparent=transparent,
        text_select=True,
    )
    webview.start()


def wait_until_server(host: str, port: int, timeout: float = 15.0) -> bool:
    import urllib.error
    import urllib.request

    url = f"http://{host}:{port}/"
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(0.15)
    return False


def run_with_overlay(
    url: str,
    ready_check: Callable[[], None] | None = None,
    *,
    width: int = 420,
    height: int = 740,
) -> None:
    """Start overlay in a thread; caller runs server/pipeline on main thread."""
    if ready_check:
        ready_check()

    overlay_thread = threading.Thread(
        target=open_overlay_window,
        kwargs={"url": url, "width": width, "height": height},
        daemon=True,
    )
    overlay_thread.start()
    while overlay_thread.is_alive():
        time.sleep(0.25)
