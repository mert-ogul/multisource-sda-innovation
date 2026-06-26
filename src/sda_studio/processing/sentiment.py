"""Lightweight sentiment analysis via TextBlob."""

from textblob import TextBlob


def sentiment_score(text: str) -> float:
    """Return polarity in [-1, 1]. Neutral/empty text → 0."""
    if not text or not text.strip():
        return 0.0
    return float(TextBlob(text).sentiment.polarity)


def average_sentiment(texts: list[str]) -> float:
    if not texts:
        return 0.0
    scores = [sentiment_score(t) for t in texts if t and t.strip()]
    if not scores:
        return 0.0
    return sum(scores) / len(scores)
