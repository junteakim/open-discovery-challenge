from __future__ import annotations

from typing import Any


def translate_lines(
    lines: list[str],
    config: dict[str, Any],
    source_lang: str | None = None,
    target_lang: str | None = None,
) -> list[str]:
    if not lines:
        return []
    tr = config.get("translation", {})
    backend = tr.get("backend", "none")
    if backend == "none":
        return lines

    if backend == "nllb":
        return _translate_nllb(lines, config, source_lang, target_lang)

    if backend == "llm":
        from meeting_copilot.llm import run_llm

        tgt = target_lang or tr.get("target_lang", "Korean")
        prompt = (
            f"Translate each line to {tgt}. "
            "Return JSON only: {\"lines\": [\"...\"]}\n\n"
            + "\n".join(lines)
        )
        out = run_llm(prompt, config)
        return out.get("lines", lines)

    return lines


def _translate_nllb(
    lines: list[str],
    config: dict[str, Any],
    source_lang: str | None,
    target_lang: str | None,
) -> list[str]:
    try:
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    except ImportError as exc:
        raise ImportError(
            "Install translation extras: pip install meeting-copilot[translate]"
        ) from exc

    tr = config.get("translation", {})
    model_name = tr.get("model", "facebook/nllb-200-distilled-600M")
    src = source_lang or tr.get("source_lang", "eng_Latn")
    tgt = target_lang or tr.get("target_lang", "kor_Hang")

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_name)
    tokenizer.src_lang = src
    forced_bos = tokenizer.convert_tokens_to_ids(tgt)

    translated: list[str] = []
    for line in lines:
        if not line.strip():
            translated.append(line)
            continue
        inputs = tokenizer(line, return_tensors="pt")
        outputs = model.generate(
            **inputs,
            forced_bos_token_id=forced_bos,
            max_new_tokens=256,
        )
        translated.append(tokenizer.batch_decode(outputs, skip_special_tokens=True)[0])
    return translated
