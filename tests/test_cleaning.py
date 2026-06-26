import sys
from datetime import date
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sda_studio.processing.cleaning import normalize_text, tokenize


class TestNormalizeText:
    def test_lowercase_and_punctuation(self):
        assert normalize_text("Hello, World!") == "hello world"

    def test_collapse_whitespace(self):
        assert normalize_text("  multiple   spaces  ") == "multiple spaces"

    def test_empty_and_none(self):
        assert normalize_text("") == ""
        assert normalize_text(None) == ""  # type: ignore[arg-type]

    def test_accents_stripped(self):
        assert "cafe" in normalize_text("café résumé")


class TestTokenize:
    def test_removes_short_tokens(self):
        tokens = tokenize("A big quiet air purifier")
        assert "quiet" in tokens
        assert "a" not in tokens

    def test_empty_input(self):
        assert tokenize("") == []
