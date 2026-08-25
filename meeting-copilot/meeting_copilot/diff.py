from __future__ import annotations

import pathlib
import sys


def transcript_delta(old: str, new: str) -> str:
    old_s = old.strip()
    new_s = new.strip()
    if not old_s:
        return new
    if new_s.startswith(old_s):
        return new_s[len(old_s):].lstrip()
    sys.stderr.write("[diff] baseline mismatch; using full transcript\n")
    return new


def read_delta_file(baseline_path: pathlib.Path, new_text: str) -> str:
    old = baseline_path.read_text(encoding="utf-8") if baseline_path.exists() else ""
    return transcript_delta(old, new_text)


def write_baseline(baseline_path: pathlib.Path, new_text: str) -> None:
    baseline_path.parent.mkdir(parents=True, exist_ok=True)
    baseline_path.write_text(new_text, encoding="utf-8")
