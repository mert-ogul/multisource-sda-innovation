"""Live patent search via the patent_client library (USPTO Public Search, optional EPO)."""

from __future__ import annotations

import logging
import os
import re
from datetime import date

from sda_studio.config.patent_search import CATEGORY_PATENT_SEARCH_TERMS
from sda_studio.config.settings import APISettings
from sda_studio.domain.models import EvidenceItem, EvidenceSource, Theme
from sda_studio.ingestion.csv_loader import DataOrigin, stamp_origin
from sda_studio.processing.cleaning import tokenize

logger = logging.getLogger(__name__)


class PatentClientSearchError(Exception):
    """Raised when patent_client is installed but a search fails."""


def is_available() -> bool:
    try:
        import patent_client  # noqa: F401

        return True
    except ImportError:
        return False


def _configure_epo_credentials(settings: APISettings) -> None:
    """Map EPO_OPS_* env vars to patent_client's expected names when needed."""
    if not settings.has_epo:
        return
    if settings.epo_consumer_key and not os.getenv("PATENT_CLIENT_EPO_API_KEY"):
        os.environ["PATENT_CLIENT_EPO_API_KEY"] = settings.epo_consumer_key
    if settings.epo_consumer_secret and not os.getenv("PATENT_CLIENT_EPO_API_SECRET"):
        os.environ["PATENT_CLIENT_EPO_API_SECRET"] = settings.epo_consumer_secret


def build_search_query(theme: Theme) -> str:
    """Build a concise full-text query from the opportunity theme."""
    parts = [theme.category.strip(), theme.text.strip()]
    query = " ".join(p for p in parts if p)
    query = re.sub(r"\s+", " ", query).strip()
    return query[:200] if len(query) > 200 else query


def build_search_queries(theme: Theme) -> list[str]:
    """Ordered USPTO queries: category anchors first, then theme phrase, then short tokens."""
    queries: list[str] = []

    for term in CATEGORY_PATENT_SEARCH_TERMS.get(theme.category, []):
        if term not in queries:
            queries.append(term)

    phrase = build_search_query(theme)
    if phrase and phrase not in queries:
        queries.append(phrase)

    tokens = [t for t in tokenize(theme.text) if len(t) > 3]
    if len(tokens) >= 2:
        short = " ".join(tokens[:3])
        if short not in queries:
            queries.append(short)

    return queries[:6]


def _first_name(names: list[str] | None) -> str:
    if not names:
        return "Unknown"
    return str(names[0]).strip() or "Unknown"


def _uspto_to_evidence(biblio, *, category: str) -> EvidenceItem | None:
    title = (biblio.patent_title or "").strip()
    if not title:
        return None

    pub_no = biblio.publication_number or ""
    appl_id = str(biblio.appl_id) if biblio.appl_id is not None else ""
    patent_id = pub_no or appl_id or "US-unknown"
    applicant = _first_name(biblio.assignee_names) or _first_name(biblio.applicant_names)
    filing_date = biblio.app_filing_date
    if filing_date is not None and not isinstance(filing_date, date):
        filing_date = None

    return EvidenceItem(
        source=EvidenceSource.PATENT,
        title=title,
        text=title,
        date=filing_date,
        category=category,
        region="US",
        relevance_score=0.0,
        metadata=stamp_origin(
            {
                "patent_id": patent_id,
                "applicant": applicant,
                "keywords": [],
                "provider": "patent_client",
                "patent_registry": "uspto_public_search",
                "publication_number": pub_no,
                "application_id": appl_id,
            },
            DataOrigin.LIVE,
        ),
    )


def _epo_to_evidence(doc, *, category: str) -> EvidenceItem | None:
    try:
        biblio = doc.biblio
    except Exception as exc:
        logger.debug("Skipping EPO hit without biblio: %s", exc)
        return None

    title = (biblio.title or "").strip()
    if not title:
        return None

    abstract = (biblio.abstract or "").strip()
    text = abstract or title
    patent_id = biblio.publication_number or biblio.docdb_number or "EP-unknown"
    applicant = _first_name(biblio.applicants_epodoc) or _first_name(biblio.applicants_original)
    region = biblio.country or "EP"

    return EvidenceItem(
        source=EvidenceSource.PATENT,
        title=title,
        text=text,
        date=None,
        category=category,
        region=region,
        relevance_score=0.0,
        metadata=stamp_origin(
            {
                "patent_id": patent_id,
                "applicant": applicant,
                "keywords": [],
                "provider": "patent_client",
                "patent_registry": "epo_inpadoc",
            },
            DataOrigin.LIVE,
        ),
    )


def _search_uspto(
    query: str,
    *,
    max_results: int,
    category: str,
    field: str = "patent_title",
) -> list[EvidenceItem]:
    from patent_client import PublicSearchBiblio

    results = PublicSearchBiblio.objects.filter(**{field: query}).limit(max_results)
    items: list[EvidenceItem] = []
    for biblio in results:
        item = _uspto_to_evidence(biblio, category=category)
        if item is not None:
            items.append(item)
    return items


def _search_uspto_multi(theme: Theme, *, max_results: int) -> list[EvidenceItem]:
    """Try category-specific and theme queries until results are found."""
    queries = build_search_queries(theme)
    for query in queries:
        for field in ("patent_title", "abstract"):
            try:
                items = _search_uspto(query, max_results=max_results, category=theme.category, field=field)
            except Exception as exc:
                logger.debug("USPTO search failed for %r (%s): %s", query, field, exc)
                continue
            if items:
                logger.info("USPTO hit %d patents for %r on %s", len(items), query, field)
                return items
    return []


def _search_epo(query: str, *, max_results: int, category: str) -> list[EvidenceItem]:
    from patent_client import Inpadoc

    results = Inpadoc.objects.filter(title_and_abstract=query).limit(max_results)
    items: list[EvidenceItem] = []
    for doc in results:
        item = _epo_to_evidence(doc, category=category)
        if item is not None:
            items.append(item)
    return items


def _dedupe(items: list[EvidenceItem]) -> list[EvidenceItem]:
    seen: set[str] = set()
    unique: list[EvidenceItem] = []
    for item in items:
        key = item.metadata.get("patent_id") or item.title
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def search_patents(theme: Theme, settings: APISettings) -> list[EvidenceItem]:
    """
    Query patent_client for patents related to the theme.

    USPTO Public Search works without API keys. EPO Inpadoc is used when
    EPO credentials are configured (EPO_OPS_* or PATENT_CLIENT_EPO_*).
    """
    if not is_available():
        raise PatentClientSearchError("patent_client is not installed")

    _configure_epo_credentials(settings)
    if not build_search_queries(theme):
        raise PatentClientSearchError("Theme text is empty — cannot search patents")

    max_results = settings.patent_client_max_results
    items: list[EvidenceItem] = []

    try:
        us_limit = max_results if not settings.has_epo else max(max_results // 2, 1)
        items.extend(_search_uspto_multi(theme, max_results=us_limit))
        logger.info(
            "patent_client USPTO search returned %d hits for category %r",
            len(items),
            theme.category,
        )
    except Exception as exc:
        raise PatentClientSearchError(f"USPTO search failed: {exc}") from exc

    if settings.has_epo:
        ep_limit = max(max_results - len(items), 0)
        query = build_search_query(theme)
        if ep_limit and query:
            try:
                epo_items = _search_epo(query, max_results=ep_limit, category=theme.category)
                items.extend(epo_items)
                logger.info("patent_client EPO search returned %d hits for %r", len(epo_items), query)
            except Exception as exc:
                logger.warning("EPO patent search failed (US results kept): %s", exc)

    items = _dedupe(items)
    if not items:
        logger.warning("patent_client returned no patents for category %r", theme.category)
    return items
