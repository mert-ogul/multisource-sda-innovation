"""Social / Reddit data connector — CSV with Reddit API extension point."""

from __future__ import annotations

import logging

from sda_studio.config.settings import APISettings
from sda_studio.domain.models import EvidenceItem, EvidenceSource
from sda_studio.ingestion.csv_loader import (
    DataOrigin,
    SourceLoadResult,
    parse_date,
    read_validated_csv,
    resolve_csv_path,
    stamp_origin,
)
from sda_studio.processing.sentiment import sentiment_score

logger = logging.getLogger(__name__)

FILENAME = "social.csv"
REQUIRED_COLUMNS = {"title", "body", "platform", "posted_date", "category", "region"}


def _safe_int(value, default: int = 0) -> int:
    if value is None or str(value) == "nan":
        return default
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def _row_to_evidence(row, *, row_index: int, file_path, origin: DataOrigin) -> EvidenceItem:
    body = str(row["body"])
    return EvidenceItem(
        source=EvidenceSource.SOCIAL,
        title=str(row["title"]),
        text=body,
        date=parse_date(row.get("posted_date"), field_name="posted_date", row_index=row_index, file_path=file_path),
        category=str(row["category"]),
        region=str(row["region"]) if row.get("region") is not None and str(row["region"]) != "nan" else None,
        relevance_score=0.0,
        metadata=stamp_origin(
            {
                "platform": str(row.get("platform", "reddit")),
                "upvotes": _safe_int(row.get("upvotes")),
                "comment_count": _safe_int(row.get("comment_count")),
                "sentiment": sentiment_score(body),
            },
            origin,
        ),
    )


def fetch_social(settings: APISettings | None = None) -> SourceLoadResult:
    if settings and settings.has_reddit:
        logger.info("Reddit credentials present — CSV fallback used until API client is implemented")

    path, origin = resolve_csv_path(FILENAME)
    if path is None:
        logger.warning("No social CSV found in data/raw or data/sample")
        return SourceLoadResult([], DataOrigin.EMPTY, None, "social")

    df = read_validated_csv(path, REQUIRED_COLUMNS)

    items = [
        _row_to_evidence(row, row_index=i, file_path=path, origin=origin)
        for i, row in df.iterrows()
    ]
    logger.info("Loaded %d social posts from %s (%s)", len(items), path, origin.value)
    return SourceLoadResult(items, origin, path, "social")
