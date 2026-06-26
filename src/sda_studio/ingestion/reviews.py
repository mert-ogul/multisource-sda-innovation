"""Review data connector — user datasets in data/raw or sample CSV fallback."""

from __future__ import annotations

import logging
import os

from sda_studio.domain.models import Theme
from sda_studio.ingestion.csv_loader import (
    DataOrigin,
    SourceLoadResult,
    parse_date,
    read_validated_csv,
    resolve_csv_path,
    stamp_origin,
)
from sda_studio.ingestion.review_sources import load_user_review_datasets, user_review_datasets_present
from sda_studio.processing.review_insights import extract_review_insights

logger = logging.getLogger(__name__)

FILENAME = "reviews.csv"
REQUIRED_COLUMNS = {"product_name", "review_text", "rating", "review_date", "category", "region"}


def _max_per_source() -> int | None:
    raw = os.getenv("REVIEWS_MAX_PER_SOURCE", "2500").strip().lower()
    if raw in {"", "0", "-1", "all", "none", "unlimited"}:
        return None
    try:
        return max(100, int(raw))
    except ValueError:
        return 2500


def _row_to_evidence(row, *, row_index: int, file_path, origin: DataOrigin):
    from sda_studio.domain.models import EvidenceItem, EvidenceSource

    text = str(row["review_text"])
    rating = row.get("rating")
    insights = extract_review_insights(text)
    return EvidenceItem(
        source=EvidenceSource.REVIEW,
        title=str(row["product_name"]),
        text=text,
        date=parse_date(row.get("review_date"), field_name="review_date", row_index=row_index, file_path=file_path),
        category=str(row["category"]),
        region=str(row["region"]) if row.get("region") is not None and str(row["region"]) != "nan" else None,
        relevance_score=0.0,
        metadata=stamp_origin(
            {
                "rating": float(rating) if rating is not None and str(rating) != "nan" else None,
                "sentiment": insights["sentiment"],
                "pain_points": insights["pain_points"],
                "desired_features": insights["desired_features"],
                "delighters": insights["delighters"],
                "topics": insights["topics"],
                "review_dataset": "reviews_csv",
            },
            origin,
        ),
    )


def _load_reviews_csv() -> SourceLoadResult:
    path, origin = resolve_csv_path(FILENAME)
    if path is None:
        logger.warning("No reviews CSV found in data/raw or data/sample")
        return SourceLoadResult([], DataOrigin.EMPTY, None, "reviews")

    df = read_validated_csv(path, REQUIRED_COLUMNS)

    items = [
        _row_to_evidence(row, row_index=i, file_path=path, origin=origin)
        for i, row in df.iterrows()
    ]
    logger.info("Loaded %d reviews from %s (%s)", len(items), path, origin.value)
    return SourceLoadResult(items, origin, path, "reviews")


def fetch_reviews(theme: Theme | None = None) -> SourceLoadResult:
    """
    Load review evidence.

    When Amazon/Yelp/coffee-maker datasets exist in data/raw, loads and filters them
    for all SDA categories. Otherwise falls back to reviews.csv in raw/sample.

    ``theme`` is reserved for future per-theme pre-filtering; matching still runs later.
    """
    _ = theme

    if user_review_datasets_present():
        items = load_user_review_datasets(max_per_source=_max_per_source())
        if items:
            by_category: dict[str, int] = {}
            for item in items:
                by_category[item.category] = by_category.get(item.category, 0) + 1
            logger.info("Review categories loaded: %s", by_category)
            return SourceLoadResult(
                items,
                DataOrigin.USER_PROVIDED,
                None,
                "reviews (Amazon + Yelp datasets)",
            )
        logger.warning("User review datasets found but produced no items; using CSV fallback")

    return _load_reviews_csv()
