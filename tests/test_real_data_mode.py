"""Tests for real-data mode (no sample back-fill)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sda_studio.config.settings import APISettings
from sda_studio.domain.models import EvidenceItem, EvidenceSource, Theme
from sda_studio.ingestion.csv_loader import DataOrigin, SourceLoadResult
from sda_studio.storage.datasets import (
    load_all_evidence,
    real_data_mode_active,
    suppress_sample_sources,
)


def _settings(*, live_news: bool = True, live_patents: bool = True) -> APISettings:
    return APISettings(
        epo_consumer_key=None,
        epo_consumer_secret=None,
        news_api_key="key",
        reddit_client_id=None,
        reddit_client_secret=None,
        reddit_user_agent="test",
        use_patent_client=live_patents,
        patent_client_max_results=25,
        use_live_news=live_news,
        news_api_max_results=25,
    )


class TestSuppressSampleSources:
    def test_suppresses_sample_when_live_present(self):
        live_news = SourceLoadResult(
            [EvidenceItem(
                source=EvidenceSource.NEWS,
                title="Live",
                text="body",
                date=None,
                category="Air",
                region=None,
                relevance_score=0.0,
            )],
            DataOrigin.LIVE,
            None,
            "news",
        )
        sample_social = SourceLoadResult(
            [],
            DataOrigin.SAMPLE,
            Path("sample/social.csv"),
            "social",
        )
        results = [
            (live_news, EvidenceSource.NEWS),
            (sample_social, EvidenceSource.SOCIAL),
        ]
        theme = Theme(text="air purifier", category="Air", time_window="Last 1 year")
        assert real_data_mode_active(results, _settings(), theme) is True
        out = suppress_sample_sources(results)
        social = next(r for r, s in out if s == EvidenceSource.SOCIAL)
        assert social.origin == DataOrigin.EMPTY

    @patch("sda_studio.storage.datasets.fetch_news")
    @patch("sda_studio.storage.datasets.fetch_patents")
    @patch("sda_studio.storage.datasets.fetch_reviews")
    @patch("sda_studio.storage.datasets.fetch_social")
    @patch("sda_studio.storage.datasets.fetch_catalog")
    @patch("sda_studio.storage.datasets.load_settings", return_value=_settings())
    @patch("sda_studio.storage.datasets.user_review_datasets_present", return_value=False)
    @patch("sda_studio.storage.datasets.synthetic_catalog_present", return_value=False)
    def test_load_all_omits_sample_when_live_news_loaded(
        self,
        _mock_catalog_flag,
        _mock_review_flag,
        _mock_settings,
        mock_catalog,
        mock_social,
        mock_reviews,
        mock_patents,
        mock_news,
    ):
        mock_news.return_value = SourceLoadResult(
            [EvidenceItem(
                source=EvidenceSource.NEWS,
                title="N",
                text="t",
                date=None,
                category="Air",
                region="US",
                relevance_score=0.0,
            )],
            DataOrigin.LIVE,
            None,
            "news (newsapi.ai)",
        )
        mock_patents.return_value = SourceLoadResult([], DataOrigin.SAMPLE, None, "patents")
        mock_reviews.return_value = SourceLoadResult([], DataOrigin.SAMPLE, None, "reviews")
        mock_social.return_value = SourceLoadResult(
            [EvidenceItem(
                source=EvidenceSource.SOCIAL,
                title="Reddit",
                text="mock",
                date=None,
                category="Air",
                region="US",
                relevance_score=0.0,
            )],
            DataOrigin.SAMPLE,
            Path("sample/social.csv"),
            "social",
        )
        mock_catalog.return_value = SourceLoadResult([], DataOrigin.SAMPLE, None, "catalog")

        theme = Theme(text="air purifier", category="Air", time_window="Last 1 year")
        _, is_sample, summaries = load_all_evidence(theme=theme)

        assert is_sample is False
        social = next(s for s in summaries if s.source == EvidenceSource.SOCIAL)
        assert social.origin == DataOrigin.EMPTY
        assert social.item_count == 0
        news = next(s for s in summaries if s.source == EvidenceSource.NEWS)
        assert news.origin == DataOrigin.LIVE
