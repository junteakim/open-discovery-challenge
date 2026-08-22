from __future__ import annotations

import json
import queue
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

LIVE_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>실시간 대면 번역</title>
  <style>
    * { box-sizing: border-box; }
    body { margin: 0; font-family: system-ui, sans-serif; background: #0f1115; color: #f2f4f8; }
    header { padding: 1rem 1.25rem; border-bottom: 1px solid #2a2f3a; }
    h1 { margin: 0; font-size: 1.25rem; }
    .meta { color: #9aa3b2; font-size: 0.9rem; margin-top: 0.35rem; }
    .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 0; min-height: calc(100vh - 72px); }
    .pane { padding: 1rem 1.25rem; overflow-y: auto; }
    .pane h2 { margin: 0 0 1rem; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.06em; color: #9aa3b2; }
    .pane.left { border-right: 1px solid #2a2f3a; background: #141820; }
    .pane.right { background: #10141c; }
    .line { margin-bottom: 1rem; animation: fade 0.2s ease; }
    .line.partial { opacity: 0.55; }
    .line .src { font-size: 1.05rem; line-height: 1.45; }
    .line .tr { font-size: 1.35rem; font-weight: 600; line-height: 1.4; color: #7db3ff; margin-top: 0.35rem; }
    .badge { display: inline-block; font-size: 0.7rem; padding: 0.15rem 0.45rem; border-radius: 999px; background: #243044; color: #b8c4d9; margin-bottom: 0.35rem; }
    .status { color: #6dd58c; }
    @keyframes fade { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: none; } }
    @media (max-width: 720px) {
      .grid { grid-template-columns: 1fr; }
      .pane.left { border-right: none; border-bottom: 1px solid #2a2f3a; }
    }
  </style>
</head>
<body>
  <header>
    <h1>실시간 대면 번역</h1>
    <div class="meta">마이크 → STT → 즉시 번역 · <span id="status" class="status">연결 중…</span></div>
  </header>
  <div class="grid">
    <section class="pane left"><h2>원문</h2><div id="source"></div></section>
    <section class="pane right"><h2>번역</h2><div id="target"></div></section>
  </div>
  <script>
    const source = document.getElementById('source');
    const target = document.getElementById('target');
    const statusEl = document.getElementById('status');
    let partialNode = null;

    function upsertLine(container, text, lang, partial) {
      if (partial) {
        if (!partialNode) {
          partialNode = document.createElement('div');
          partialNode.className = 'line partial';
          partialNode.innerHTML = `<div class="badge">${lang}</div><div class="src"></div>`;
          container.prepend(partialNode);
        }
        partialNode.querySelector('.src').textContent = text;
        return;
      }
      partialNode = null;
      const el = document.createElement('div');
      el.className = 'line';
      el.innerHTML = `<div class="badge">${lang}</div><div class="src"></div>`;
      el.querySelector('.src').textContent = text;
      container.prepend(el);
    }

    function addTranslation(text, lang) {
      const el = document.createElement('div');
      el.className = 'line';
      el.innerHTML = `<div class="badge">${lang}</div><div class="tr"></div>`;
      el.querySelector('.tr').textContent = text;
      target.prepend(el);
    }

    const es = new EventSource('/stream');
    es.onopen = () => { statusEl.textContent = '실시간 수신 중'; };
    es.onerror = () => { statusEl.textContent = '연결 끊김 — 새로고침'; };
    es.onmessage = (ev) => {
      const seg = JSON.parse(ev.data);
      if (seg.partial) {
        upsertLine(source, seg.text, seg.lang, true);
        return;
      }
      upsertLine(source, seg.text, seg.lang, false);
      addTranslation(seg.translated, seg.target_lang);
    };
  </script>
</body>
</html>
"""


class LiveHub:
    def __init__(self) -> None:
        self._clients: list[queue.Queue[str]] = []
        self._lock = threading.Lock()

    def subscribe(self) -> queue.Queue[str]:
        q: queue.Queue[str] = queue.Queue(maxsize=256)
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


def make_handler(hub: LiveHub):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, _fmt, *_args) -> None:
            return

        def do_GET(self) -> None:
            if self.path in ("/", "/index.html"):
                body = LIVE_HTML.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return

            if self.path == "/stream":
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

    return Handler


def run_live_server(hub: LiveHub, host: str, port: int) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), make_handler(hub))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
