from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

PACKAGE_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG = PACKAGE_ROOT / "config.yaml"
CONTEXT_DIR = PACKAGE_ROOT / "context"


def load_config(path: Path | None = None) -> dict[str, Any]:
    cfg_path = path or DEFAULT_CONFIG
    if not cfg_path.is_file():
        example = PACKAGE_ROOT / "config.example.yaml"
        if example.is_file():
            data = yaml.safe_load(example.read_text(encoding="utf-8")) or {}
            return apply_profile(data, data.get("profile"))
        return {}
    data = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
    return apply_profile(data, data.get("profile"))


def apply_profile(config: dict[str, Any], profile: str | None) -> dict[str, Any]:
    if not profile:
        return config
    profiles = config.get("profiles") or {}
    patch = profiles.get(profile)
    if not patch:
        return config
    merged = dict(config)
    for key, val in patch.items():
        if key == "profiles":
            continue
        if isinstance(val, dict) and isinstance(merged.get(key), dict):
            merged[key] = {**merged[key], **val}
        else:
            merged[key] = val
    merged["profile"] = profile
    return merged


def load_ontology(context_dir: Path | None = None) -> dict[str, Any]:
    base = context_dir or CONTEXT_DIR
    path = base / "ontology.json"
    if not path.is_file():
        path = base / "ontology.example.json"
    if not path.is_file():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_memory(context_dir: Path | None = None) -> str:
    base = context_dir or CONTEXT_DIR
    path = base / "memory.md"
    if not path.is_file():
        path = base / "memory.example.md"
    if not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


from meeting_copilot.ontology import ontology_prompt_block


def build_context_block(context_dir: Path | None = None) -> str:
    ontology = load_ontology(context_dir)
    memory = load_memory(context_dir)
    parts: list[str] = []
    if ontology:
        block = ontology_prompt_block(ontology)
        if block:
            parts.append(block)
        else:
            parts.append("## Ontology (structured context)\n")
            parts.append(json.dumps(ontology, indent=2, ensure_ascii=False))
    if memory.strip():
        parts.append("\n## Pre-meeting memory\n")
        parts.append(memory.strip())
    return "\n".join(parts)
