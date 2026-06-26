"""News data connector — live newsapi.ai search or CSV fallback."""

from __future__ import annotations

import logging

import requests

from sda_studio.config.settings import APISettings, load_settings
from sda_studio.domain.models import Theme
from sda_studio.ingestion import newsapi_source
from sda_studio.ingestion.csv_loader import (
    DataOrigin,
    SourceLoadResult,
    parse_date,
    read_validated_csv,
    resolve_csv_path,
    stamp_origin,
)

logger = logging.getLogger(__name__)

FILENAME = "news.csv"
REQUIRED_COLUMNS = {"headline", "snippet", "source_name", "published_date", "category", "region"}


def _row_to_evidence(row, *, row_index: int, file_path, origin: DataOrigin):
    from sda_studio.domain.models import EvidenceItem, EvidenceSource

    entities_raw = row.get("entities", "")
    entities = (
        [e.strip() for e in str(entities_raw).split(",") if e.strip()]
        if entities_raw is not None and str(entities_raw) != "nan"
        else []
    )
    return EvidenceItem(
        source=EvidenceSource.NEWS,
        title=str(row["headline"]),
        text=str(row["snippet"]),
        date=parse_date(
            row.get("published_date"),
            field_name="published_date",
            row_index=row_index,
            file_path=file_path,
        ),
        category=str(row["category"]),
        region=str(row["region"]) if row.get("region") is not None and str(row["region"]) != "nan" else None,
        relevance_score=0.0,
        metadata=stamp_origin(
            {"source_name": str(row["source_name"]), "entities": entities},
            origin,
        ),
    )


def _load_news_csv() -> SourceLoadResult:
    path, origin = resolve_csv_path(FILENAME)
    if path is None:
        logger.warning("No news CSV found in data/raw or data/sample")
        return SourceLoadResult([], DataOrigin.EMPTY, None, "news")

    df = read_validated_csv(path, REQUIRED_COLUMNS)

    items = [
        _row_to_evidence(row, row_index=i, file_path=path, origin=origin)
        for i, row in df.iterrows()
    ]
    logger.info("Loaded %d news items from %s (%s)", len(items), path, origin.value)
    return SourceLoadResult(items, origin, path, "news")


def fetch_news(settings: APISettings | None = None, theme: Theme | None = None) -> SourceLoadResult:
    """
    Load news for analysis.

    When NEWS_API_KEY is set, USE_LIVE_NEWS=true, and a theme is provided, queries
    newsapi.ai (Event Registry). Otherwise loads from CSV in data/raw or data/sample.
    """
    settings = settings or load_settings()

    if settings.live_news_enabled and theme is not None:
        try:
            items = newsapi_source.search_news(theme, settings)
            if items:
                logger.info("Loaded %d live news articles via newsapi.ai", len(items))
                return SourceLoadResult(items, DataOrigin.LIVE, None, "news (newsapi.ai)")
            logger.warning("newsapi.ai returned no articles; falling back to CSV")
        except newsapi_source.NewsApiSearchError as exc:
            logger.warning("newsapi.ai search failed, using CSV fallback: %s", exc)
        except requests.RequestException as exc:
            logger.warning("newsapi.ai network error, using CSV fallback: %s", exc)
        except Exception as exc:
            logger.warning("Unexpected newsapi.ai error, using CSV fallback: %s", exc)

    return _load_news_csv()
