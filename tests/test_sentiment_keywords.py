"""Initial tests for sentiment and keyword helpers."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sda_studio.processing.keywords import extract_top_keywords
from sda_studio.processing.sentiment import average_sentiment, sentiment_score


def test_sentiment_negative_review():
    score = sentiment_score("too loud at night, filter is expensive and annoying")
    assert score < 0.2


def test_sentiment_positive_review():
    score = sentiment_score("love how quiet and compact this air purifier is")
    assert score > 0


def test_average_sentiment_empty():
    assert average_sentiment([]) == 0.0


def test_extract_keywords_from_reviews():
    texts = [
        "quiet hepa air purifier for bedroom",
        "silent compact filter for small apartment",
        "noisy fan at night in bedroom",
    ]
    keywords = extract_top_keywords(texts, top_n=5)
    assert len(keywords) >= 1
    joined = " ".join(keywords)
    assert "quiet" in joined or "bedroom" in joined or "purifier" in joined
