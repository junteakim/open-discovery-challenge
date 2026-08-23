from __future__ import annotations

import json
import queue
import threading
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any, Callable

from meeting_copilot.live.copilot_engine import CopilotBrain


SMOOTH_HTML = """<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Meeting Copilot</title>
  <style>
    :root { --bg:#0c0e12; --card:#151922; --line:#252b38; --text:#eef1f6; --muted:#8b95a8; --accent:#5b8cff; --green:#5dd68a; --warn:#ffcc66; }
    * { box-sizing:border-box; }
    body { margin:0; font-family:-apple-system,BlinkMacSystemFont,system-ui,sans-serif; background:var(--bg); color:var(--text); }
    .shell { max-width:420px; margin:0 auto; min-height:100vh; display:flex; flex-direction:column; border-left:1px solid var(--line); border-right:1px solid var(--line); }
    header { padding:14px 16px 10px; border-bottom:1px solid var(--line); }
    h1 { margin:0; font-size:15px; font-weight:600; }
    .sub { color:var(--muted); font-size:12px; margin-top:4px; }
    .tabs { display:flex; gap:6px; padding:10px 12px; border-bottom:1px solid var(--line); }
    .tabs button { flex:1; border:1px solid var(--line); background:transparent; color:var(--muted); border-radius:8px; padding:8px; cursor:pointer; font-size:12px; }
    .tabs button.active { background:var(--card); color:var(--text); border-color:var(--accent); }
    .actions { display:flex; flex-wrap:wrap; gap:6px; padding:8px 12px; border-bottom:1px solid var(--line); }
    .chip { border:1px solid var(--line); background:var(--card); color:var(--text); border-radius:999px; padding:6px 10px; font-size:11px; cursor:pointer; }
    .chip:hover { border-color:var(--accent); }
    main { flex:1; overflow:auto; padding:12px; }
    .panel { display:none; }
    .panel.active { display:block; }
    .line { margin-bottom:12px; padding-bottom:10px; border-bottom:1px solid var(--line); }
    .line.partial { opacity:.5; }
    .src { font-size:13px; line-height:1.45; }
    .tr { font-size:15px; font-weight:600; color:var(--accent); margin-top:4px; line-height:1.4; }
    .badge { font-size:10px; color:var(--muted); text-transform:uppercase; letter-spacing:.05em; }
    .card { background:var(--card); border:1px solid var(--line); border-radius:12px; padding:12px; margin-bottom:10px; }
    .card h3 { margin:0 0 8px; font-size:12px; color:var(--muted); text-transform:uppercase; }
    .card p { margin:0; font-size:14px; line-height:1.5; white-space:pre-wrap; }
    .card .native { margin-top:8px; color:var(--green); font-size:13px; }
    .highlight { display:inline-block; background:#24304a; color:#b8d0ff; border-radius:6px; padding:2px 6px; margin:2px 4px 2px 0; font-size:11px; }
    .suggestion { border-color:var(--warn); }
    footer { padding:8px 12px; border-top:1px solid var(--line); font-size:11px; color:var(--muted); }
    .status { color:var(--green); }
  </style>
</head>
<body>
  <div class="shell">
    <header>
      <h1>Meeting Copilot</h1>
      <div class="sub">Smooth-style · local · <span id="status" class="status">connecting…</span></div>
    </header>
    <nav class="tabs">
      <button type="button" data-tab="live" class="active">Live</button>
      <button type="button" data-tab="brief">Brief</button>
      <button type="button" data-tab="compose">Compose</button>
    </nav>
    <div class="actions">
      <button class="chip" data-compose="agree">Agree</button>
      <button class="chip" data-compose="disagree">Disagree</button>
      <button class="chip" data-compose="question">Question</button>
      <button class="chip" data-compose="suggestion">Suggestion</button>
    </div>
    <main>
      <section id="live" class="panel active">
        <div id="suggestion-card" class="card suggestion" style="display:none">
          <h3>Suggested reply</h3>
          <p id="suggestion-text"></p>
          <p id="suggestion-native" class="native"></p>
        </div>
        <div id="feed"></div>
      </section>
      <section id="brief" class="panel">
        <div class="card"><h3>Live summary</h3><p id="brief-text">Generating first summary…</p></div>
        <div id="highlights"></div>
      </section>
      <section id="compose" class="panel">
        <div class="card"><h3>Compose</h3><p id="compose-text">Tap Agree / Disagree / Question / Suggestion above.</p><p id="compose-native" class="native"></p></div>
      </section>
    </main>
    <footer>Pin this window on your Mac · ontology + memory injected · audio not stored</footer>
  </div>
  <script>
    const feed = document.getElementById('feed');
    const statusEl = document.getElementById('status');
    let partialEl = null;

    document.querySelectorAll('.tabs button').forEach(btn => {
      btn.addEventListener('click', () => {
        document.querySelectorAll('.tabs button').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));
        btn.classList.add('active');
        document.getElementById(btn.dataset.tab).classList.add('active');
      });
    });

    document.querySelectorAll('[data-compose]').forEach(chip => {
      chip.addEventListener('click', async () => {
        await fetch('/compose', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({mode: chip.dataset.compose}),
        });
        document.querySelector('[data-tab="compose"]').click();
      });
    });

    function addLine(text, translated, partial) {
      if (partial) {
        if (!partialEl) {
          partialEl = document.createElement('div');
          partialEl.className = 'line partial';
          partialEl.innerHTML = '<div class="badge">live</div><div class="src"></div><div class="tr"></div>';
          feed.prepend(partialEl);
        }
        partialEl.querySelector('.src').textContent = text;
        partialEl.querySelector('.tr').textContent = translated;
        return;
      }
      partialEl = null;
      const el = document.createElement('div');
      el.className = 'line';
      el.innerHTML = '<div class="badge">final</div><div class="src"></div><div class="tr"></div>';
      el.querySelector('.src').textContent = text;
      el.querySelector('.tr').textContent = translated;
      feed.prepend(el);
    }

    const es = new EventSource('/stream');
    es.onopen = () => { statusEl.textContent = 'live'; };
    es.onerror = () => { statusEl.textContent = 'reconnect…'; };
    es.onmessage = (ev) => {
      const msg = JSON.parse(ev.data);
      if (msg.type === 'segment') {
        addLine(msg.text, msg.translated, msg.partial);
        return;
      }
      if (msg.type === 'brief') {
        document.getElementById('brief-text').textContent = msg.brief || '';
        const hl = document.getElementById('highlights');
        hl.innerHTML = (msg.highlights || []).map(h => `<span class="highlight">${h}</span>`).join('');
        return;
      }
      if (msg.type === 'suggestion') {
        const card = document.getElementById('suggestion-card');
        card.style.display = 'block';
        document.getElementById('suggestion-text').textContent = msg.reply;
        document.getElementById('suggestion-native').textContent = msg.reply_native || '';
        return;
      }
      if (msg.type === 'compose') {
        document.getElementById('compose-text').textContent = msg.reply;
        document.getElementById('compose-native').textContent = msg.reply_native || '';
      }
    };
  </script>
</body>
</html>
"""


@dataclass
class LiveHub:
    _clients: list[queue.Queue[str]] = field(default_factory=list)
    _lock: threading.Lock = field(default_factory=threading.Lock)
    brain: CopilotBrain | None = None

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

        def do_GET(self) -> None:
            if self.path in ("/", "/index.html"):
                body = SMOOTH_HTML.encode("utf-8")
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


def run_live_server(hub: LiveHub, host: str, port: int) -> ThreadingHTTPServer:
    server = ThreadingHTTPServer((host, port), make_handler(hub))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server
