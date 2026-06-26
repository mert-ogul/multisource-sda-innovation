"""Theme matching: keyword overlap + TF-IDF cosine similarity."""

from __future__ import annotations

import logging
from datetime import date, timedelta

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from sda_studio.config.categories import TIME_WINDOW_YEARS, TimeWindow
from sda_studio.domain.models import EvidenceItem, Theme
from sda_studio.processing.cleaning import normalize_text, tokenize

logger = logging.getLogger(__name__)


def _theme_keywords(theme_text: str) -> set[str]:
    return set(tokenize(theme_text))


def _keyword_overlap_score(theme_tokens: set[str], doc_tokens: set[str]) -> float:
    if not theme_tokens or not doc_tokens:
        return 0.0
    overlap = len(theme_tokens & doc_tokens)
    return overlap / len(theme_tokens)


def _cosine_similarity(theme_text: str, doc_text: str) -> float:
    theme_norm = normalize_text(theme_text)
    doc_norm = normalize_text(doc_text)
    if not theme_norm or not doc_norm:
        return 0.0
    vectorizer = TfidfVectorizer(stop_words="english")
    try:
        matrix = vectorizer.fit_transform([theme_norm, doc_norm])
        return float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0])
    except ValueError:
        return 0.0


def _within_time_window(item_date: date | None, window: TimeWindow, reference: date) -> bool:
    years = TIME_WINDOW_YEARS.get(window)
    if years is None or item_date is None:
        return True
    cutoff = reference - timedelta(days=365 * years)
    return item_date >= cutoff


def match_evidence_to_theme(
    theme: Theme,
    items: list[EvidenceItem],
    *,
    reference_date: date | None = None,
    min_score: float = 0.08,
) -> list[EvidenceItem]:
    """Filter and rank evidence by category, time window, region, and relevance."""
    ref = reference_date or date.today()
    try:
        window = TimeWindow(theme.time_window)
    except ValueError:
        logger.warning("Unknown time window %r — using all sample data", theme.time_window)
        window = TimeWindow.ALL

    theme_tokens = _theme_keywords(theme.text)
    matched: list[EvidenceItem] = []

    for item in items:
        if item.category != theme.category and theme.category != "All":
            continue
        if theme.region and item.region and item.region != theme.region:
            continue
        if not _within_time_window(item.date, window, ref):
            continue

        doc_tokens = set(tokenize(f"{item.title} {item.text}"))
        overlap = _keyword_overlap_score(theme_tokens, doc_tokens)
        cosine = _cosine_similarity(theme.text, f"{item.title} {item.text}")
        score = 0.45 * overlap + 0.55 * cosine

        if theme.category and theme.category.lower() in normalize_text(item.text):
            score += 0.05

        if score < min_score:
            continue

        explanation = (
            f"Keyword overlap {overlap:.0%}, TF-IDF similarity {cosine:.0%} "
            f"for theme tokens: {', '.join(sorted(theme_tokens)[:6])}"
        )
        item.relevance_score = round(score, 3)
        item.match_explanation = explanation
        matched.append(item)

    matched.sort(key=lambda e: e.relevance_score, reverse=True)
    return matched


def explain_matching(theme: Theme, count: int) -> str:
    return (
        f"Matched {count} items using keyword overlap + TF-IDF cosine similarity, "
        f"filtered by category '{theme.category}' and window '{theme.time_window}'"
        + (f" in region '{theme.region}'" if theme.region else "")
        + "."
    )
