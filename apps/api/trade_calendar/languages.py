import hashlib
import re

# Hangul syllables, Jamo and compatibility Jamo, plus Japanese kana.
FOREIGN_SCRIPT = re.compile(
    r"[\u1100-\u11ff\u3040-\u30ff\u3130-\u318f\ua960-\ua97f\uac00-\ud7ff\uff66-\uff9f]"
)


def needs_translation(text: str | None) -> bool:
    return bool(text and FOREIGN_SCRIPT.search(text))


def translation_key(text: str) -> str:
    return hashlib.sha256(f"zh-CN\0{text.strip()}".encode()).hexdigest()


def display_text(
    text: str | None,
    translations: dict[str, str],
    fallback: str | None = None,
    placeholder: str = "翻译中",
) -> str:
    original = (text or "").strip()
    if original and not needs_translation(original):
        return original
    translated = translations.get(original, "").strip()
    if translated and not needs_translation(translated):
        return translated
    if fallback and not needs_translation(fallback):
        return fallback.strip()
    return placeholder
