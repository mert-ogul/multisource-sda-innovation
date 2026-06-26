"""Tests for newsapi.ai live news integration."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sda_studio.config.settings import APISettings
from sda_studio.domain.models import EvidenceSource, Theme
from sda_studio.ingestion.csv_loader import DataOrigin
from sda_studio.ingestion import newsapi_source
from sda_studio.ingestion.news import fetch_news
from sda_studio.storage.datasets import analyze_theme


def _settings(*, use_live_news: bool = True, api_key: str | None = "test-key") -> APISettings:
    return APISettings(
        epo_consumer_key=None,
        epo_consumer_secret=None,
        news_api_key=api_key,
        reddit_client_id=None,
        reddit_client_secret=None,
        reddit_user_agent="test",
        use_patent_client=False,
        patent_client_max_results=25,
        use_live_news=use_live_news,
        news_api_max_results=10,
    )


SAMPLE_RESPONSE = {
    "articles": {
        "totalResults": 1,
        "page": 1,
        "count": 1,
        "pages": 1,
        "results": [
            {
                "uri": "123",
                "lang": "eng",
                "date": "2025-06-01",
                "title": "New quiet air purifier targets small bedrooms",
                "body": "Manufacturers are launching compact HEPA purifiers with night mode.",
                "url": "https://example.com/article",
                "source": {
                    "uri": "example.com",
                    "title": "Tech News",
                    "location": {"label": "United States"},
                },
                "concepts": [
                    {"label": {"eng": "Air purifier"}},
                    {"label": {"eng": "HEPA"}},
                ],
            }
        ],
    }
}


class TestNewsApiSource:
    def test_build_keywords_uses_full_phrase_for_long_themes(self):
        theme = Theme(text="silent compact air purifier", category="Air", time_window="Last 1 year")
        keywords = newsapi_source.build_keywords(theme)
        assert keywords == ["silent compact air purifier"]

    def test_build_keywords_uses_tokens_for_short_themes(self):
        theme = Theme(text="hepa purifier", category="Air", time_window="Last 1 year")
        keywords = newsapi_source.build_keywords(theme)
        assert keywords == ["hepa", "purifier"]

    def test_article_mapping(self):
        item = newsapi_source._article_to_evidence(
            SAMPLE_RESPONSE["articles"]["results"][0],
            category="Air",
        )
        assert item is not None
        assert item.title.startswith("New quiet air purifier")
        assert item.metadata["data_origin"] == "live"
        assert item.metadata["provider"] == "newsapi.ai"
        assert "Air purifier" in item.metadata["entities"]

    @patch("sda_studio.ingestion.newsapi_source._fetch_articles")
    def test_search_news_success(self, mock_fetch):
        mock_fetch.return_value = [
            newsapi_source._article_to_evidence(
                SAMPLE_RESPONSE["articles"]["results"][0],
                category="Air",
            )
        ]

        theme = Theme(text="air purifier", category="Air", time_window="Last 1 year")
        items = newsapi_source.search_news(theme, _settings())
        assert len(items) == 1
        mock_fetch.assert_called()

    @patch("sda_studio.ingestion.newsapi_source._fetch_articles")
    def test_search_news_tries_relaxed_keywords(self, mock_fetch):
        mock_fetch.side_effect = [[], [newsapi_source._article_to_evidence(
            SAMPLE_RESPONSE["articles"]["results"][0],
            category="Air",
        )]]

        theme = Theme(text="silent compact air purifier", category="Air", time_window="Last 1 year")
        items = newsapi_source.search_news(theme, _settings())
        assert len(items) == 1
        assert mock_fetch.call_count == 2

    @patch("sda_studio.ingestion.newsapi_source.requests.get")
    def test_fetch_articles_handles_401(self, mock_get):
        mock_response = MagicMock()
        mock_response.ok = False
        mock_response.status_code = 401
        mock_response.text = "limit reached"
        mock_response.reason = "Unauthorized"
        mock_get.return_value = mock_response

        theme = Theme(text="air purifier", category="Air", time_window="Last 1 year")
        with pytest.raises(newsapi_source.NewsApiSearchError, match="token limit"):
            newsapi_source._fetch_articles(["air purifier"], settings=_settings(), theme=theme)


class TestFetchNewsLive:
    @patch("sda_studio.ingestion.newsapi_source.search_news")
    def test_live_news_when_enabled(self, mock_search, ensure_sample_data):
        from sda_studio.domain.models import EvidenceItem

        mock_search.return_value = [
            EvidenceItem(
                source=EvidenceSource.NEWS,
                title="Live headline",
                text="Live snippet",
                date=date(2025, 1, 1),
                category="Air",
                region="US",
                relevance_score=0.0,
                metadata={"source_name": "Tech News", "data_origin": "live"},
            )
        ]
        theme = Theme(text="air purifier", category="Air", time_window="Last 1 year")
        result = fetch_news(_settings(), theme=theme)
        assert result.origin == DataOrigin.LIVE
        assert result.items[0].title == "Live headline"

    def test_csv_fallback_without_theme(self, ensure_sample_data):
        result = fetch_news(_settings(), theme=None)
        assert result.origin == DataOrigin.SAMPLE

    def test_csv_fallback_without_api_key(self, ensure_sample_data):
        theme = Theme(text="air purifier", category="Air", time_window="Last 1 year")
        result = fetch_news(_settings(api_key=None), theme=theme)
        assert result.origin == DataOrigin.SAMPLE

    @patch("sda_studio.ingestion.newsapi_source.search_news", side_effect=requests.Timeout("timed out"))
    def test_csv_fallback_on_network_error(self, _mock_search, ensure_sample_data):
        theme = Theme(text="air purifier", category="Air", time_window="Last 1 year")
        result = fetch_news(_settings(), theme=theme)
        assert result.origin == DataOrigin.SAMPLE


@pytest.fixture(scope="module")
def ensure_sample_data():
    from sda_studio.config.settings import SAMPLE_DIR

    if not (SAMPLE_DIR / "news.csv").exists():
        import subprocess

        subprocess.run([sys.executable, str(ROOT / "scripts" / "generate_sample_data.py")], check=True)


class TestAnalyzeThemeWithLiveNews:
    @patch("sda_studio.ingestion.newsapi_source.search_news")
    def test_analyze_theme_uses_live_news(self, mock_search, ensure_sample_data):
        from sda_studio.domain.models import EvidenceItem

        mock_search.return_value = [
            EvidenceItem(
                source=EvidenceSource.NEWS,
                title="HEPA purifier trend grows",
                text="Demand for quiet bedroom purifiers is rising.",
                date=date(2025, 5, 1),
                category="Air",
                region="US",
                relevance_score=0.0,
                metadata={"source_name": "Tech News", "data_origin": "live"},
            )
        ]
        theme = Theme(text="hepa air purifier", category="Air", time_window="Last 1 year")
        with patch("sda_studio.storage.datasets.load_settings", return_value=_settings()):
            loaded = analyze_theme(theme)

        news_summary = next(s for s in loaded.sources if s.source == EvidenceSource.NEWS)
        assert news_summary.origin == DataOrigin.LIVE
        assert loaded.is_sample_data is False
