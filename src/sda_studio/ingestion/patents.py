"""Patent data connector — live patent_client search or CSV fallback."""

from __future__ import annotations

import logging

from sda_studio.config.settings import APISettings, load_settings
from sda_studio.domain.models import Theme
from sda_studio.ingestion.csv_loader import (
    DataOrigin,
    SourceLoadResult,
    parse_date,
    read_validated_csv,
    resolve_csv_path,
    stamp_origin,
)
from sda_studio.ingestion import patent_client_source

logger = logging.getLogger(__name__)

FILENAME = "patents.csv"
REQUIRED_COLUMNS = {"patent_id", "title", "abstract", "applicant", "filing_date", "category", "region"}


def _row_to_evidence(row, *, row_index: int, file_path, origin: DataOrigin):
    from sda_studio.domain.models import EvidenceItem, EvidenceSource

    keywords_raw = row.get("keywords", "")
    keywords = (
        [k.strip() for k in str(keywords_raw).split(",") if k.strip()]
        if keywords_raw is not None and str(keywords_raw) != "nan"
        else []
    )
    return EvidenceItem(
        source=EvidenceSource.PATENT,
        title=str(row["title"]),
        text=str(row["abstract"]),
        date=parse_date(row.get("filing_date"), field_name="filing_date", row_index=row_index, file_path=file_path),
        category=str(row["category"]),
        region=str(row["region"]) if row.get("region") is not None and str(row["region"]) != "nan" else None,
        relevance_score=0.0,
        metadata=stamp_origin(
            {
                "patent_id": str(row["patent_id"]),
                "applicant": str(row["applicant"]),
                "keywords": keywords,
            },
            origin,
        ),
    )


def _load_patents_csv() -> SourceLoadResult:
    path, origin = resolve_csv_path(FILENAME)
    if path is None:
        logger.warning("No patent CSV found in data/raw or data/sample")
        return SourceLoadResult([], DataOrigin.EMPTY, None, "patents")

    df = read_validated_csv(path, REQUIRED_COLUMNS)

    items = [
        _row_to_evidence(row, row_index=i, file_path=path, origin=origin)
        for i, row in df.iterrows()
    ]
    logger.info("Loaded %d patents from %s (%s)", len(items), path, origin.value)
    return SourceLoadResult(items, origin, path, "patents")


def fetch_patents(settings: APISettings | None = None, theme: Theme | None = None) -> SourceLoadResult:
    """
    Load patents for analysis.

    When USE_PATENT_CLIENT=true and a theme is provided, queries USPTO (and optionally
    EPO) via patent_client. Otherwise loads from CSV in data/raw or data/sample.
    """
    settings = settings or load_settings()

    if settings.use_patent_client and theme is not None:
        if patent_client_source.is_available():
            try:
                items = patent_client_source.search_patents(theme, settings)
                if items:
                    logger.info("Loaded %d live patents via patent_client", len(items))
                    return SourceLoadResult(items, DataOrigin.LIVE, None, "patents (patent_client)")
                logger.warning("patent_client returned no results for theme %r", theme.text)
            except patent_client_source.PatentClientSearchError as exc:
                logger.warning("patent_client search failed: %s", exc)
            except Exception as exc:
                logger.warning("Unexpected patent_client error: %s", exc)
        else:
            logger.warning(
                "USE_PATENT_CLIENT is enabled but patent_client is not installed "
                "(requires Python 3.11–3.12)."
            )
        return SourceLoadResult([], DataOrigin.EMPTY, None, "patents (live — no results)")

    return _load_patents_csv()
