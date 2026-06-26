"""Unified dataset loading and evidence aggregation."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from sda_studio.config.settings import APISettings, RAW_DIR, load_settings
from sda_studio.domain.models import EvidenceItem, EvidenceSource, Theme
from sda_studio.ingestion.catalog_sources import synthetic_catalog_present
from sda_studio.ingestion.csv_loader import DataOrigin, SourceLoadResult
from sda_studio.ingestion.catalog import fetch_catalog
from sda_studio.ingestion.news import fetch_news
from sda_studio.ingestion.patents import fetch_patents
from sda_studio.ingestion.review_sources import user_review_datasets_present
from sda_studio.ingestion.reviews import fetch_reviews
from sda_studio.ingestion.social import fetch_social
from sda_studio.processing.matching import match_evidence_to_theme

logger = logging.getLogger(__name__)

REAL_ORIGINS = frozenset({DataOrigin.LIVE, DataOrigin.USER_PROVIDED})

STANDARD_CSV_SOURCES = (
    "patents.csv",
    "news.csv",
    "reviews.csv",
    "social.csv",
    "product_catalog.csv",
)


@dataclass(frozen=True)
class SourceSummary:
    source: EvidenceSource
    item_count: int
    origin: DataOrigin
    path: str | None
    label: str


@dataclass
class LoadedEvidence:
    all_items: list[EvidenceItem]
    matched_items: list[EvidenceItem]
    is_sample_data: bool
    regions_available: list[str]
    sources: list[SourceSummary] = field(default_factory=list)

    @property
    def data_mode_label(self) -> str:
        if self.is_sample_data:
            return "Sample/demo data (all sources)"
        live = [s for s in self.sources if s.origin == DataOrigin.LIVE]
        user = [s for s in self.sources if s.origin == DataOrigin.USER_PROVIDED]
        if live or user:
            parts: list[str] = []
            if live:
                parts.append(f"{len(live)} live API source(s)")
            if user:
                parts.append(f"{len(user)} user dataset(s)")
            empty = sum(1 for s in self.sources if s.origin == DataOrigin.EMPTY)
            suffix = f"; {empty} source(s) omitted (no real data)" if empty else ""
            return "Real data mode — " + ", ".join(parts) + suffix
        return "No data loaded"


def _summary(result: SourceLoadResult, source: EvidenceSource) -> SourceSummary:
    return SourceSummary(
        source=source,
        item_count=len(result.items),
        origin=result.origin,
        path=str(result.path) if result.path else None,
        label=result.label,
    )


def _has_user_csv_in_raw(filename: str, raw_dir: Path = RAW_DIR) -> bool:
    return (raw_dir / filename).exists()


def real_data_mode_active(
    results: list[tuple[SourceLoadResult, EvidenceSource]],
    settings: APISettings,
    theme: Theme | None,
) -> bool:
    """True when the app should not back-fill missing sources with sample/demo CSVs."""
    if any(result.origin in REAL_ORIGINS for result, _ in results):
        return True
    if user_review_datasets_present() or synthetic_catalog_present():
        return True
    if any(_has_user_csv_in_raw(name) for name in STANDARD_CSV_SOURCES):
        return True
    if theme is not None and (settings.use_patent_client or settings.live_news_enabled):
        return True
    return False


def suppress_sample_sources(
    results: list[tuple[SourceLoadResult, EvidenceSource]],
) -> list[tuple[SourceLoadResult, EvidenceSource]]:
    """Replace sample/demo loads with empty results when real data mode is on."""
    suppressed: list[tuple[SourceLoadResult, EvidenceSource]] = []
    for result, source in results:
        if result.origin == DataOrigin.SAMPLE:
            logger.info(
                "Omitting sample %s — real data mode active (not mixing demo data)",
                source.value,
            )
            suppressed.append(
                (
                    SourceLoadResult([], DataOrigin.EMPTY, None, result.source_name),
                    source,
                )
            )
        else:
            suppressed.append((result, source))
    return suppressed


def _compute_is_sample(origins: list[DataOrigin], *, real_mode: bool) -> bool:
    non_empty = [o for o in origins if o != DataOrigin.EMPTY]
    if not non_empty:
        return not real_mode
    return all(o == DataOrigin.SAMPLE for o in non_empty)


def load_all_evidence(
    theme: Theme | None = None,
) -> tuple[list[EvidenceItem], bool, list[SourceSummary]]:
    """Load and merge evidence from all sources. Returns items, sample flag, per-source summaries."""
    settings = load_settings()
    results: list[tuple[SourceLoadResult, EvidenceSource]] = [
        (fetch_patents(settings, theme=theme), EvidenceSource.PATENT),
        (fetch_news(settings, theme=theme), EvidenceSource.NEWS),
        (fetch_reviews(theme=theme), EvidenceSource.REVIEW),
        (fetch_social(settings), EvidenceSource.SOCIAL),
        (fetch_catalog(), EvidenceSource.CATALOG),
    ]

    real_mode = real_data_mode_active(results, settings, theme)
    if real_mode:
        results = suppress_sample_sources(results)

    all_items: list[EvidenceItem] = []
    summaries: list[SourceSummary] = []
    origins: list[DataOrigin] = []

    for result, source in results:
        all_items.extend(result.items)
        summaries.append(_summary(result, source))
        origins.append(result.origin)

    is_sample = _compute_is_sample(origins, real_mode=real_mode)

    logger.info(
        "Loaded %d evidence items across %d sources (sample_mode=%s, real_data_mode=%s)",
        len(all_items),
        len(summaries),
        is_sample,
        real_mode,
    )
    return all_items, is_sample, summaries


def available_regions(items: list[EvidenceItem]) -> list[str]:
    return sorted({i.region for i in items if i.region})


def analyze_theme(theme: Theme) -> LoadedEvidence:
    all_items, is_sample, sources = load_all_evidence(theme=theme)
    matched = match_evidence_to_theme(theme, list(all_items))
    return LoadedEvidence(
        all_items=all_items,
        matched_items=matched,
        is_sample_data=is_sample,
        regions_available=available_regions(all_items),
        sources=sources,
    )
