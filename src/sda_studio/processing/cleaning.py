"""Text normalization utilities."""

import re
import unicodedata


def normalize_text(text: str) -> str:
    """Lowercase, strip accents, collapse whitespace, remove punctuation noise."""
    if not text or not isinstance(text, str):
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def tokenize(text: str) -> list[str]:
    normalized = normalize_text(text)
    if not normalized:
        return []
    tokens = [t for t in normalized.split() if len(t) > 2]
    return tokens
