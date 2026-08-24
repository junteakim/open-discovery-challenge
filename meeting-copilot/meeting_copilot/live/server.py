from __future__ import annotations

import json
import queue
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from meeting_copilot.live.copilot_engine import CopilotBrain

STATIC_DIR = Path(__file__).resolve().parent / "static"


@dataclass
class LiveHub:
    _clients: list[queue.Queue[str]] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    brain: CopilotBrain | None = None
    context_dir: str | None = None

    def subscribe(self) -> queue.Queue[str]:
        q: queue.Queue[str] = queue.Queue(maxsize=512)
        with self._lock:
            self._clients.append(q)
        return q

    def unsubscribe(self, q: queue.Queue[str]) -> None:
        with self._lock:
            if q in self._clients:
                self._clients.remove(q)

    def publish(self, payload: dict[str, Any]) -> None:
        data = json.dumps(payload, ensure_ascii=False)
        with self._lock:
            dead: list[queue.Queue[str]] = []
            for q in self._clients:
                try:
                    q.put_nowait(data)
                except queue.Queue.Full:
                    dead.append(q)
            for q in dead:
                self._clients.remove(q)

    def glossary_json(self) -> list[dict[str, str]]:
        from meeting_copilot.ontology import glossary_for_ui

        return glossary_for_ui(self.context_dir)


def _content_type(path: Path) -> str:
    suffix = path.suffix.lower()
    return {
        ".html": "text/html; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".js": "application/javascript; charset=utf-8",
    }.get(suffix, "application/octet-stream")


def make_handler(hub: LiveHub):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _fmt, *_args) -> None:
            return

        def _read_json_body(self) -> dict[str, Any]:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length) if length else b"{}"
            try:
                return json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError:
                return {}

        def _send_bytes(self, body: bytes, content_type: str) -> None:
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self) -> None:
            path = self.path.split("?", 1)[0]

            if path in ("/", "/index.html"):
                body = (STATIC_DIR / "index.html").read_bytes()
                self._send_bytes(body, "text/html; charset=utf-8")
                return

            if path.startswith("/static/"):
                rel = path[len("/static/") :]
                file_path = (STATIC_DIR / rel).resolve()
                if not str(file_path).startswith(str(STATIC_DIR.resolve())):
                    self.send_error(403)
                    return
                if file_path.is_file():
                    self._send_bytes(file_path.read_bytes(), _content_type(file_path))
                    return
                self.send_error(404)
                return

            if path == "/glossary":
                body = json.dumps(hub.glossary_json(), ensure_ascii=False).encode("utf-8")
                self._send_bytes(body, "application/json; charset=utf-8")
                return

            if path == "/stream":
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                self.send_header("Cache-Control", "no-cache")
                self.send_header("Connection", "keep-alive")
                self.end_headers()
                q = hub.subscribe()
                try:
                    self.wfile.write(b": connected\n\n")
                    self.wfile.flush()
                    while True:
                        try:
                            data = q.get(timeout=15)
                        except queue.Empty:
                            self.wfile.write(b": ping\n\n")
                            self.wfile.flush()
                            continue
                        msg = f"data: {data}\n\n".encode("utf-8")
                        self.wfile.write(msg)
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                finally:
                    hub.unsubscribe(q)
                return

            self.send_error(404)

        def do_POST(self) -> None:
            if self.path == "/compose":
                body = self._read_json_body()
                mode = str(body.get("mode", "suggestion"))
                utterance = body.get("utterance")
                if hub.brain:
                    hub.brain.compose(mode, utterance)
                self.send_response(204)
                self.end_headers()
                return
            self.send_error(404)

    return Handler


def run_live_server(
    hub: LiveHub,
    host: str,
    port: int,
    *,
    context_dir: str | None = None,
) -> ThreadingHTTPServer:
    hub.context_dir = context_dir
    server = ThreadingHTTPServer((host, port), make_handler(hub))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
