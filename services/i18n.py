"""
i18n — Translation lookup with startup key-set validation.
"""
import json
import os
from functools import lru_cache

SUPPORTED_LANGS = ["zh", "en", "km"]
DEFAULT_LANG = "zh"

_LOCALES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "locales")


@lru_cache(maxsize=3)
def _load(lang: str) -> dict:
    path = os.path.join(_LOCALES_DIR, f"{lang}.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _collect_keys(d: dict, prefix: str = "") -> set[str]:
    """Recursively collect all dot-notation keys from a nested dict."""
    keys = set()
    for k, v in d.items():
        full = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict):
            keys.update(_collect_keys(v, full))
        else:
            keys.add(full)
    return keys


def validate_locales() -> None:
    """Assert all locale files have identical key sets. Called at startup."""
    ref_lang = SUPPORTED_LANGS[0]
    ref_keys = _collect_keys(_load(ref_lang))
    for lang in SUPPORTED_LANGS[1:]:
        lang_keys = _collect_keys(_load(lang))
        missing = ref_keys - lang_keys
        extra = lang_keys - ref_keys
        if missing:
            raise KeyError(f"Locale '{lang}' missing keys vs '{ref_lang}': {missing}")
        if extra:
            raise KeyError(f"Locale '{lang}' has extra keys vs '{ref_lang}': {extra}")


def t(key: str, lang: str, **kwargs) -> str:
    """Lookup translation by dot-notation key, interpolate {placeholders}."""
    data = _load(lang if lang in SUPPORTED_LANGS else DEFAULT_LANG)
    val = data
    for k in key.split("."):
        if isinstance(val, dict):
            val = val.get(k, key)
        else:
            return key  # key path doesn't match structure
    if isinstance(val, list):
        return val  # return list as-is (for option arrays)
    return val.format(**kwargs) if kwargs and isinstance(val, str) else val


def get_lang(context) -> str:
    """Get user's selected language from context."""
    return context.user_data.get("lang", DEFAULT_LANG)
