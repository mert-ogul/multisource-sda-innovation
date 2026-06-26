"""Pain points, desired features, and delighters from review text."""

from __future__ import annotations

from sda_studio.processing.cleaning import normalize_text, tokenize
from sda_studio.processing.keywords import STOPWORDS, extract_top_keywords
from sda_studio.processing.sentiment import sentiment_score

PAIN_TERMS = {
    "noise", "noisy", "loud", "leak", "leaks", "leaking", "broken", "breaks",
    "difficult", "hard", "messy", "smell", "odor", "expensive", "cheap",
    "bulky", "heavy", "awkward", "frustrating", "annoying", "slow", "clog",
    "clogged", "dirty", "stain", "stains", "defective", "returned", "waste",
    "overheat", "burn", "scratch", "scratches", "unreliable", "flaw", "flawed",
    "disappointing", "poor", "worst", "hate", "terrible", "awful", "bad",
    "cleaning", "maintenance", "filter", "app", "bug", "bugs", "wifi",
}

DESIRE_TERMS = {
    "quiet", "silent", "compact", "small", "efficient", "energy", "easy",
    "simple", "affordable", "portable", "lightweight", "smart", "preset",
    "presets", "auto", "automatic", "self", "clean", "cordless", "solo",
    "apartment", "low", "fast", "quick", "convenient", "programmable",
    "hepa", "filter", "preset", "timer", "compact", "space", "saving",
}

DELIGHT_TERMS = {
    "love", "loved", "amazing", "excellent", "perfect", "fantastic", "great",
    "wonderful", "delicious", "tasty", "smooth", "quiet", "easy", "fast",
    "recommend", "impressed", "happy", "pleased", "favorite", "best",
    "beautiful", "sleek", "sturdy", "reliable", "worth", "game", "changer",
}


def _find_terms(text: str, vocabulary: set[str]) -> list[str]:
    tokens = set(tokenize(text))
    hits = sorted(tokens & vocabulary)
    normalized = normalize_text(text)
    for term in vocabulary:
        if " " in term and term in normalized and term not in hits:
            hits.append(term)
    return hits


def extract_review_insights(text: str) -> dict[str, list[str] | float]:
    """
    Return sentiment plus recurring pain points, desired features, and delighters.

    Uses cleaned tokens and simple lexicons — suitable for demo-scale review mining.
    """
    cleaned = normalize_text(text)
    if not cleaned:
        return {
            "sentiment": 0.0,
            "pain_points": [],
            "desired_features": [],
            "delighters": [],
            "topics": [],
        }

    pain_points = _find_terms(text, PAIN_TERMS)
    desired_features = _find_terms(text, DESIRE_TERMS)
    delighters = _find_terms(text, DELIGHT_TERMS)

    # Topic keywords: TF-IDF on this review's sentences, minus stopwords.
    topics = extract_top_keywords([text], top_n=6)
    topics = [t for t in topics if t not in STOPWORDS]

    return {
        "sentiment": sentiment_score(text),
        "pain_points": pain_points[:8],
        "desired_features": desired_features[:8],
        "delighters": delighters[:8],
        "topics": topics,
    }
