"""Live news search via newsapi.ai (Event Registry API)."""

from __future__ import annotations

import logging
from datetime import date, timedelta

import requests

from sda_studio.config.categories import TIME_WINDOW_YEARS, TimeWindow
from sda_studio.config.settings import APISettings
from sda_studio.domain.models import EvidenceItem, EvidenceSource, Theme
from sda_studio.ingestion.csv_loader import DataOrigin, stamp_origin
from sda_studio.processing.cleaning import tokenize

logger = logging.getLogger(__name__)

API_URL = "https://eventregistry.org/api/v1/article/getArticles"
REQUEST_TIMEOUT_SECONDS = 30
MAX_KEYWORDS = 10
BODY_SNIPPET_LEN = 600


class NewsApiSearchError(Exception):
    """Raised when the Event Registry API request fails."""


def build_keywords(theme: Theme) -> list[str]:
    """
    Build keyword list for Event Registry search.

    Uses the full theme phrase when possible; otherwise up to four salient
    tokens combined with AND. Trial accounts allow up to 15 keywords per query.
    """
    phrase = " ".join(theme.text.split())
    if len(phrase.split()) >= 3:
        return [phrase[:120]]

    tokens = [t for t in tokenize(theme.text) if len(t) > 2]
    if len(tokens) >= 2:
        return tokens[:MAX_KEYWORDS]

    if phrase:
        return [phrase[:120]]
    category = theme.category.strip()
    return [category] if category else []


def _date_start(theme: Theme) -> str | None:
    try:
        window = TimeWindow(theme.time_window)
    except ValueError:
        return None

    years = TIME_WINDOW_YEARS.get(window)
    if years is None:
        return None
    return (date.today() - timedelta(days=365 * years)).isoformat()


def _parse_article_date(article: dict) -> date | None:
    raw = article.get("date")
    if isinstance(raw, str) and raw:
        try:
            return date.fromisoformat(raw[:10])
        except ValueError:
            pass

    raw_dt = article.get("dateTime") or article.get("dateTimePub")
    if isinstance(raw_dt, str) and len(raw_dt) >= 10:
        try:
            return date.fromisoformat(raw_dt[:10])
        except ValueError:
            return None
    return None


def _snippet(body: str | None) -> str:
    text = (body or "").strip()
    if not text:
        return ""
    if len(text) <= BODY_SNIPPET_LEN:
        return text
    return text[:BODY_SNIPPET_LEN].rstrip() + "…"


def _extract_entities(article: dict) -> list[str]:
    entities: list[str] = []
    for concept in article.get("concepts") or []:
        label = concept.get("label")
        if isinstance(label, dict):
            name = label.get("eng") or next(iter(label.values()), "")
        elif isinstance(label, str):
            name = label
        else:
            name = ""
        name = str(name).strip()
        if name and name not in entities:
            entities.append(name)
    return entities[:12]


def _extract_region(article: dict) -> str | None:
    source = article.get("source") or {}
    location = source.get("location") or {}
    label = location.get("label")
    if isinstance(label, dict):
        return label.get("eng") or next(iter(label.values()), None)
    if isinstance(label, str) and label.strip():
        return label.strip()
    return None


def _article_to_evidence(article: dict, *, category: str) -> EvidenceItem | None:
    title = (article.get("title") or "").strip()
    if not title:
        return None

    body = _snippet(article.get("body"))
    text = body or title
    source_info = article.get("source") or {}
    source_name = (source_info.get("title") or source_info.get("uri") or "Unknown").strip()

    return EvidenceItem(
        source=EvidenceSource.NEWS,
        title=title,
        text=text,
        date=_parse_article_date(article),
        category=category,
        region=_extract_region(article),
        relevance_score=0.0,
        metadata=stamp_origin(
            {
                "source_name": source_name,
                "entities": _extract_entities(article),
                "provider": "newsapi.ai",
                "article_uri": article.get("uri"),
                "url": article.get("url"),
                "lang": article.get("lang"),
            },
            DataOrigin.LIVE,
        ),
    )


def _raise_for_status(response: requests.Response) -> None:
    if response.ok:
        return

    message = response.text[:300] if response.text else response.reason
    if response.status_code == 401:
        raise NewsApiSearchError("NewsAPI.ai token limit reached (HTTP 401).")
    if response.status_code == 403:
        raise NewsApiSearchError(f"NewsAPI.ai access forbidden (HTTP 403): {message}")
    if response.status_code == 429:
        raise NewsApiSearchError("NewsAPI.ai rate limit exceeded (HTTP 429). Retry sequentially.")
    if response.status_code == 400:
        raise NewsApiSearchError(f"NewsAPI.ai bad request (HTTP 400): {message}")
    raise NewsApiSearchError(f"NewsAPI.ai request failed (HTTP {response.status_code}): {message}")


def _relaxed_keywords(theme: Theme) -> list[str]:
    """Fallback keywords when the full phrase returns no articles."""
    tokens = [t for t in tokenize(theme.text) if len(t) > 3]
    if len(tokens) >= 2:
        return tokens[:4]
    return []


def _fetch_articles(
    keywords: list[str],
    *,
    settings: APISettings,
    theme: Theme,
) -> list[EvidenceItem]:
    keyword_oper = "and" if len(keywords) > 1 else "or"
    params: list[tuple[str, str | int | bool]] = [
        ("apiKey", settings.news_api_key),
        ("resultType", "articles"),
        ("lang", "eng"),
        ("articlesCount", min(settings.news_api_max_results, 100)),
        ("articlesPage", 1),
        ("articlesSortBy", "date"),
        ("articlesSortByAsc", False),
        ("keywordOper", keyword_oper),
        ("keywordLoc", "body,title"),
        ("includeArticleTitle", True),
        ("includeArticleBody", True),
        ("includeArticleConcepts", True),
        ("includeSourceTitle", True),
        ("dataType", "news"),
    ]
    for keyword in keywords:
        params.append(("keyword", keyword))

    date_start = _date_start(theme)
    if date_start:
        params.append(("dateStart", date_start))

    logger.info("newsapi.ai search keywords=%s oper=%s dateStart=%s", keywords, keyword_oper, date_start)
    response = requests.get(API_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
    _raise_for_status(response)

    try:
        payload = response.json()
    except ValueError as exc:
        raise NewsApiSearchError("NewsAPI.ai returned non-JSON response") from exc

    articles = (payload.get("articles") or {}).get("results") or []
    items: list[EvidenceItem] = []
    for article in articles:
        item = _article_to_evidence(article, category=theme.category)
        if item is not None:
            items.append(item)
    return items


def search_news(theme: Theme, settings: APISettings) -> list[EvidenceItem]:
    """Query Event Registry for articles matching the opportunity theme."""
    if not settings.has_news_api:
        raise NewsApiSearchError("NEWS_API_KEY is not configured")

    keyword_sets = [build_keywords(theme)]
    relaxed = _relaxed_keywords(theme)
    if relaxed and relaxed != keyword_sets[0]:
        keyword_sets.append(relaxed)

    last_error: Exception | None = None
    for keywords in keyword_sets:
        if not keywords:
            continue
        try:
            items = _fetch_articles(keywords, settings=settings, theme=theme)
        except NewsApiSearchError as exc:
            last_error = exc
            continue
        if items:
            logger.info("newsapi.ai returned %d articles for keywords=%s", len(items), keywords)
            return items

    if last_error is not None:
        raise last_error

    logger.warning("newsapi.ai returned no articles for theme %r", theme.text)
    return []
