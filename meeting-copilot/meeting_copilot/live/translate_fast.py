from __future__ import annotations

from typing import Any

# User-facing aliases → (whisper_code, nllb_code)
LANG_ALIASES: dict[str, tuple[str, str]] = {
    "ko": ("ko", "kor_Hang"),
    "kor": ("ko", "kor_Hang"),
    "korean": ("ko", "kor_Hang"),
    "en": ("en", "eng_Latn"),
    "eng": ("en", "eng_Latn"),
    "english": ("en", "eng_Latn"),
    "ja": ("ja", "jpn_Jpan"),
    "jpn": ("ja", "jpn_Jpan"),
    "japanese": ("ja", "jpn_Jpan"),
    "zh": ("zh", "zho_Hans"),
    "cmn": ("zh", "zho_Hans"),
    "chinese": ("zh", "zho_Hans"),
    "es": ("es", "spa_Latn"),
    "spanish": ("es", "spa_Latn"),
    "fr": ("fr", "fra_Latn"),
    "french": ("fr", "fra_Latn"),
    "de": ("de", "deu_Latn"),
    "german": ("de", "deu_Latn"),
}


def resolve_lang(code: str) -> tuple[str, str]:
    key = code.strip().lower().replace("_", "-").split("-")[0]
    if key in LANG_ALIASES:
        return LANG_ALIASES[key]
    if "_" in code:
        whisper = code.split("_")[0][:2]
        return whisper, code
    raise ValueError(f"Unknown language code: {code!r}. Use ko, en, ja, ...")


MARIAN_MODELS: dict[tuple[str, str], str] = {
    ("en", "ko"): "Helsinki-NLP/opus-mt-en-ko",
    ("ko", "en"): "Helsinki-NLP/opus-mt-ko-en",
    ("en", "ja"): "Helsinki-NLP/opus-mt-en-jap",
    ("ja", "en"): "Helsinki-NLP/opus-mt-jap-en",
    ("en", "zh"): "Helsinki-NLP/opus-mt-en-zh",
    ("zh", "en"): "Helsinki-NLP/opus-mt-zh-en",
    ("en", "es"): "Helsinki-NLP/opus-mt-en-es",
    ("es", "en"): "Helsinki-NLP/opus-mt-es-en",
    ("en", "fr"): "Helsinki-NLP/opus-mt-en-fr",
    ("fr", "en"): "Helsinki-NLP/opus-mt-fr-en",
    ("en", "de"): "Helsinki-NLP/opus-mt-en-de",
    ("de", "en"): "Helsinki-NLP/opus-mt-de-en",
}


class FastTranslator:
    """Low-latency translator: MarianMT for common pairs, NLLB fallback."""

    def __init__(self, config: dict[str, Any]) -> None:
        self._config = config
        self._marian: dict[tuple[str, str], Any] = {}
        self._nllb_tokenizer = None
        self._nllb_model = None

    def translate(self, text: str, src_whisper: str, tgt_whisper: str) -> str:
        text = text.strip()
        if not text:
            return ""
        pair = (src_whisper, tgt_whisper)
        if pair in MARIAN_MODELS:
            return self._marian_translate(text, pair)
        return self._nllb_translate(text, src_whisper, tgt_whisper)

    def _marian_translate(self, text: str, pair: tuple[str, str]) -> str:
        try:
            from transformers import MarianMTModel, MarianTokenizer
        except ImportError as exc:
            raise ImportError(
                "Install live extras: pip install meeting-copilot[live]"
            ) from exc

        if pair not in self._marian:
            name = MARIAN_MODELS[pair]
            self._marian[pair] = (
                MarianTokenizer.from_pretrained(name),
                MarianMTModel.from_pretrained(name),
            )
        tokenizer, model = self._marian[pair]
        batch = tokenizer([text], return_tensors="pt", padding=True)
        outputs = model.generate(**batch, max_new_tokens=128)
        return tokenizer.decode(outputs[0], skip_special_tokens=True)

    def _nllb_translate(self, text: str, src_whisper: str, tgt_whisper: str) -> str:
        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        except ImportError as exc:
            raise ImportError(
                "Install live extras: pip install meeting-copilot[live]"
            ) from exc

        tr = self._config.get("translation", {})
        model_name = tr.get("model", "facebook/nllb-200-distilled-600M")
        _, src_nllb = resolve_lang(src_whisper)
        _, tgt_nllb = resolve_lang(tgt_whisper)

        if self._nllb_tokenizer is None:
            self._nllb_tokenizer = AutoTokenizer.from_pretrained(model_name)
            self._nllb_model = AutoModelForSeq2SeqLM.from_pretrained(model_name)

        tokenizer = self._nllb_tokenizer
        model = self._nllb_model
        assert tokenizer is not None and model is not None

        tokenizer.src_lang = src_nllb
        forced_bos = tokenizer.convert_tokens_to_ids(tgt_nllb)
        inputs = tokenizer(text, return_tensors="pt")
        outputs = model.generate(**inputs, forced_bos_token_id=forced_bos, max_new_tokens=128)
        return tokenizer.batch_decode(outputs, skip_special_tokens=True)[0]
