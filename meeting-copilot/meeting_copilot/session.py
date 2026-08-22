from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

SESSIONS_ROOT = Path(__file__).resolve().parent.parent / "sessions"

APP_TEMPLATE = {
    "index.html": """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Meeting Copilot</title>
  <link rel="stylesheet" href="styles.css" />
</head>
<body>
  <header>
    <h1 id="meeting-title">Meeting Copilot</h1>
    <p id="meeting-meta"></p>
    <nav id="tabs"></nav>
  </header>
  <main id="content"></main>
  <footer><small>Refresh after UPDATE · Local only</small></footer>
  <script type="module" src="app.js"></script>
</body>
</html>
""",
    "styles.css": """:root { font-family: system-ui, sans-serif; color: #111; background: #f6f7f9; }
body { max-width: 960px; margin: 0 auto; padding: 1rem; }
header { margin-bottom: 1rem; }
nav button { margin: 0.25rem; padding: 0.4rem 0.8rem; border: 1px solid #ccc; background: #fff; cursor: pointer; }
nav button.active { background: #1a5cff; color: #fff; border-color: #1a5cff; }
.card { background: #fff; border-radius: 8px; padding: 1rem; margin-bottom: 0.75rem; box-shadow: 0 1px 3px rgba(0,0,0,.08); }
.card h2 { margin-top: 0; font-size: 1rem; }
ul { padding-left: 1.2rem; }
#translation .line { padding: 0.25rem 0; border-bottom: 1px solid #eee; }
""",
    "app.js": """import { briefingTab } from './tabs/briefing.js';
import { questionsTab } from './tabs/questions.js';
import { topicsTab } from './tabs/topics.js';
import { decisionsTab } from './tabs/decisions.js';
import { followupsTab } from './tabs/followups.js';
import { translationTab } from './tabs/translation.js';
import { renderTabs } from './components.js';

const meta = document.getElementById('meeting-meta');
const titleEl = document.getElementById('meeting-title');
if (meta) meta.textContent = 'Second screen · ontology + memory injected';

const tabs = [
  { id: 'briefing', label: 'Briefing', render: briefingTab },
  { id: 'questions', label: 'Questions', render: questionsTab },
  { id: 'topics', label: 'Topics', render: topicsTab },
  { id: 'decisions', label: 'Decisions', render: decisionsTab },
  { id: 'followups', label: 'Follow-ups', render: followupsTab },
  { id: 'translation', label: 'Translation', render: translationTab },
];

renderTabs(tabs, 'briefing');
""",
    "components.js": """export function card(title, bodyHtml) {
  return `<section class="card"><h2>${title}</h2>${bodyHtml}</section>`;
}

export function renderTabs(tabs, defaultId) {
  const nav = document.getElementById('tabs');
  const content = document.getElementById('content');
  if (!nav || !content) return;

  let active = defaultId;
  function show(id) {
    active = id;
    nav.querySelectorAll('button').forEach((b) => {
      b.classList.toggle('active', b.dataset.tab === id);
    });
    const tab = tabs.find((t) => t.id === id);
    content.innerHTML = tab ? tab.render() : '';
  }

  nav.innerHTML = tabs
    .map((t) => `<button type="button" data-tab="${t.id}">${t.label}</button>`)
    .join('');
  nav.querySelectorAll('button').forEach((btn) => {
    btn.addEventListener('click', () => show(btn.dataset.tab));
  });
  show(active);
}
""",
}


def slugify(text: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:48] or "meeting"


def session_dir(title: str, when: date | None = None) -> Path:
    d = when or date.today()
    return SESSIONS_ROOT / f"{d.isoformat()}-{slugify(title)}"


def write_tab_js(path: Path, export_name: str, data: dict[str, Any]) -> None:
    path.write_text(
        f"export const {export_name} = {json.dumps(data, ensure_ascii=False, indent=2)};\n",
        encoding="utf-8",
    )


def create_session(
    title: str,
    meeting_type: str,
    participants: list[str],
    llm_data: dict[str, Any],
) -> Path:
    root = session_dir(title)
    if root.exists():
        raise FileExistsError(f"Session already exists: {root}")

    app = root / "app"
    tabs = app / "tabs"
    state = root / "state"
    tabs.mkdir(parents=True)
    state.mkdir(parents=True)

    for name, content in APP_TEMPLATE.items():
        dest = app / name
        if "/" in name:
            continue
        dest.write_text(content, encoding="utf-8")

    tab_files = {
        "briefing.js": ("briefing", {
            "title": title,
            "type": meeting_type,
            "goal": llm_data.get("goal", ""),
            "participants": participants or llm_data.get("participants", []),
            "constraints": llm_data.get("constraints", []),
            "summary": llm_data.get("briefing_summary", ""),
        }),
        "questions.js": ("questions", {"groups": llm_data.get("opening_questions", [])}),
        "topics.js": ("topics", {"items": llm_data.get("planned_topics", [])}),
        "decisions.js": ("decisions", {"decisions": [], "risks": []}),
        "followups.js": ("followups", {"items": [], "draft": ""}),
        "translation.js": ("translation", {"lines": []}),
    }
    for fname, (export_name, data) in tab_files.items():
        write_tab_js(tabs / fname, export_name, data)

    (state / "transcript.txt").write_text("", encoding="utf-8")
    (state / "captions.log").write_text("", encoding="utf-8")

    write_tab_render_modules(app)

    meta = {
        "title": title,
        "type": meeting_type,
        "participants": participants,
    }
    (root / "session.json").write_text(
        json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return root


def apply_update(session: Path, llm_data: dict[str, Any]) -> None:
    tabs = session / "app" / "tabs"

    def merge_list_file(name: str, export_key: str, field: str) -> None:
        path = tabs / name
        if not path.exists():
            return
        text = path.read_text(encoding="utf-8")
        m = re.search(r"=\s*(\{[\s\S]*\});", text)
        current = json.loads(m.group(1)) if m else {}
        new_items = llm_data.get(field, [])
        if isinstance(current.get("items"), list):
            seen = set(current["items"])
            for item in new_items:
                if item not in seen:
                    current["items"].append(item)
                    seen.add(item)
        elif isinstance(current.get("groups"), list):
            for item in new_items:
                if item not in current["groups"]:
                    current["groups"].append(item)
        write_tab_js(path, export_key, current)

    merge_list_file("questions.js", "questions", "questions")
    merge_list_file("topics.js", "topics", "topics")
    merge_list_file("decisions.js", "decisions", "decisions")
    merge_list_file("followups.js", "followups", "followups")

    dec_path = tabs / "decisions.js"
    if dec_path.exists():
        text = dec_path.read_text(encoding="utf-8")
        m = re.search(r"=\s*(\{[\s\S]*\});", text)
        current = json.loads(m.group(1)) if m else {}
        for risk in llm_data.get("risks", []):
            if risk not in current.get("risks", []):
                current.setdefault("risks", []).append(risk)
        write_tab_js(dec_path, "decisions", current)

    tr_lines = llm_data.get("translation_lines", [])
    if tr_lines:
        tr_path = tabs / "translation.js"
        text = tr_path.read_text(encoding="utf-8")
        m = re.search(r"=\s*(\{[\s\S]*\});", text)
        current = json.loads(m.group(1)) if m else {"lines": []}
        current.setdefault("lines", []).extend(tr_lines)
        write_tab_js(tr_path, "translation", current)


def write_close_summary(session: Path, llm_data: dict[str, Any]) -> Path:
    lines = ["# Meeting Summary", "", "## Outcome", "", llm_data.get("outcome", ""), "", "## Decisions"]
    for d in llm_data.get("decisions", []):
        lines.append(f"- {d}")
    lines.extend(["", "## Action Items", "", "| Item | Owner | Due | Status |", "| --- | --- | --- | --- |"])
    for row in llm_data.get("action_items", []):
        if isinstance(row, dict):
            lines.append(
                f"| {row.get('item','')} | {row.get('owner','')} | {row.get('due','')} | {row.get('status','')} |"
            )
        else:
            lines.append(f"| {row} | | | |")
    lines.extend(["", "## Open Questions"])
    for q in llm_data.get("open_questions", []):
        lines.append(f"- {q}")
    lines.extend(["", "## Follow-up Draft", "", llm_data.get("followup_draft", "")])
    out = session / "summary.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


# Tab render modules (static exports consumed by dashboard)
BRIEFING_TAB = """import { card } from '../components.js';

export function briefingTab() {
  const b = briefing;
  const parts = [
    card('Goal', `<p>${b.goal || '—'}</p>`),
    card('Summary', `<p>${b.summary || '—'}</p>`),
    card('Participants', `<ul>${(b.participants || []).map((p) => `<li>${p}</li>`).join('')}</ul>`),
    card('Constraints', `<ul>${(b.constraints || []).map((c) => `<li>${c}</li>`).join('')}</ul>`),
  ];
  return parts.join('');
}
"""

QUESTIONS_TAB = """import { card } from '../components.js';

export function questionsTab() {
  const items = questions.groups || [];
  if (!items.length) return card('Live questions', '<p>Waiting for transcript…</p>');
  return card('Live questions', `<ul>${items.map((q) => `<li>${q}</li>`).join('')}</ul>`);
}
"""

TOPICS_TAB = """import { card } from '../components.js';

export function topicsTab() {
  const items = topics.items || [];
  return card('Topics', `<ul>${items.map((t) => `<li>${t}</li>`).join('')}</ul>`);
}
"""

DECISIONS_TAB = """import { card } from '../components.js';

export function decisionsTab() {
  const d = decisions.decisions || [];
  const r = decisions.risks || [];
  return [
    card('Decisions', `<ul>${d.map((x) => `<li>${x}</li>`).join('')}</ul>`),
    card('Risks', `<ul>${r.map((x) => `<li>${x}</li>`).join('')}</ul>`),
  ].join('');
}
"""

FOLLOWUPS_TAB = """import { card } from '../components.js';

export function followupsTab() {
  const items = followups.items || [];
  return card('Follow-ups', `<ul>${items.map((x) => `<li>${x}</li>`).join('')}</ul>`);
}
"""

TRANSLATION_TAB = """import { card } from '../components.js';

export function translationTab() {
  const lines = translation.lines || [];
  const body = lines.map((l) => `<div class="line">${l}</div>`).join('') || '<p>—</p>';
  return card('Translation', body);
}
"""


def write_tab_render_modules(app: Path) -> None:
    mapping = {
        "briefing.js": BRIEFING_TAB,
        "questions.js": QUESTIONS_TAB,
        "topics.js": TOPICS_TAB,
        "decisions.js": DECISIONS_TAB,
        "followups.js": FOLLOWUPS_TAB,
        "translation.js": TRANSLATION_TAB,
    }
    tabs = app / "tabs"
    for fname, content in mapping.items():
        path = tabs / fname
        if path.exists():
            data_part = path.read_text(encoding="utf-8")
            path.write_text(data_part + "\n" + content, encoding="utf-8")
