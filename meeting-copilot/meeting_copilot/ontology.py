from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def normalize_ontology(raw: dict[str, Any]) -> dict[str, Any]:
    """Accept plain JSON or JSON-LD (@context / @graph)."""
    if "@graph" in raw:
        graph = raw["@graph"]
        entities = [n for n in graph if isinstance(n, dict)]
        terms = raw.get("terms", {})
        return {"format": "json-ld", "entities": entities, "terms": terms, "context": raw.get("@context")}
    if "@context" in raw and "entities" not in raw:
        return {"format": "json-ld", "entities": [raw], "terms": raw.get("terms", {})}
    return {"format": "plain", **raw}


def ontology_prompt_block(raw: dict[str, Any], max_entities: int = 24) -> str:
    """Compact ontology for LLM prompts (token-efficient)."""
    if not raw:
        return ""

    norm = normalize_ontology(raw)
    lines: list[str] = ["### Ontology (injected)"]

    terms = norm.get("terms") or {}
    if terms:
        lines.append("**Terms:**")
        for key, val in list(terms.items())[:30]:
            lines.append(f"- {key}: {val}")

    entities = norm.get("entities") or []
    if entities:
        lines.append("**Entities:**")
        for ent in entities[:max_entities]:
            if not isinstance(ent, dict):
                continue
            label = ent.get("labels", ent.get("name", ent.get("id", ent.get("@id", "?"))))
            if isinstance(label, dict):
                label = label.get("en") or next(iter(label.values()), "?")
            etype = ent.get("type", ent.get("@type", ""))
            facts = ent.get("facts", [])
            fact = facts[0] if facts else ent.get("description", "")
            lines.append(f"- [{etype}] {label}: {fact}")

    relations = norm.get("relations") or []
    if relations:
        lines.append("**Relations:**")
        for rel in relations[:20]:
            if isinstance(rel, dict):
                lines.append(f"- {rel.get('from', '?')} --{rel.get('type', '?')}--> {rel.get('to', '?')}")

    return "\n".join(lines)


def load_and_format_ontology(path: Path | None = None, context_dir: Path | None = None) -> str:
    from meeting_copilot.config import CONTEXT_DIR, load_ontology

    base = context_dir or CONTEXT_DIR
    raw = load_ontology(base)
    if path and path.is_file():
        raw = json.loads(path.read_text(encoding="utf-8"))
    return ontology_prompt_block(raw)
