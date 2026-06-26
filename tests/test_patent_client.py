"""Tests for patent_client live patent integration."""

from __future__ import annotations

import sys
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sda_studio.config.settings import APISettings
from sda_studio.domain.models import EvidenceSource, Theme
from sda_studio.ingestion.csv_loader import DataOrigin
from sda_studio.ingestion import patent_client_source
from sda_studio.ingestion.patents import fetch_patents
from sda_studio.storage.datasets import analyze_theme


def _settings(*, use_patent_client: bool = True) -> APISettings:
    return APISettings(
        epo_consumer_key=None,
        epo_consumer_secret=None,
        news_api_key=None,
        reddit_client_id=None,
        reddit_client_secret=None,
        reddit_user_agent="test",
        use_patent_client=use_patent_client,
        patent_client_max_results=10,
        use_live_news=False,
        news_api_max_results=25,
    )


class TestPatentClientSource:
    def test_build_search_query_combines_category_and_theme(self):
        theme = Theme(text="silent compact purifier", category="Air", time_window="12m")
        assert patent_client_source.build_search_query(theme) == "Air silent compact purifier"

    def test_build_search_queries_prefers_category_terms(self):
        theme = Theme(text="silent compact purifier", category="Air", time_window="12m")
        queries = patent_client_source.build_search_queries(theme)
        assert queries[0] == "air purifier"

    def test_uspto_mapping(self):
        biblio = MagicMock()
        biblio.patent_title = "HEPA air purifier"
        biblio.publication_number = "1234567"
        biblio.appl_id = "16/000001"
        biblio.assignee_names = ["Acme Corp"]
        biblio.applicant_names = []
        biblio.app_filing_date = date(2024, 1, 15)

        item = patent_client_source._uspto_to_evidence(biblio, category="Air")
        assert item is not None
        assert item.title == "HEPA air purifier"
        assert item.metadata["data_origin"] == "live"
        assert item.metadata["provider"] == "patent_client"
        assert item.region == "US"

    @patch("sda_studio.ingestion.patent_client_source._search_uspto")
    def test_search_patents_dedupes(self, mock_us):
        mock_us.return_value = [
            patent_client_source._uspto_to_evidence(
                MagicMock(
                    patent_title="A",
                    publication_number="1",
                    appl_id="1",
                    assignee_names=["X"],
                    applicant_names=[],
                    app_filing_date=None,
                ),
                category="Air",
            ),
            patent_client_source._uspto_to_evidence(
                MagicMock(
                    patent_title="A duplicate",
                    publication_number="1",
                    appl_id="1",
                    assignee_names=["X"],
                    applicant_names=[],
                    app_filing_date=None,
                ),
                category="Air",
            ),
        ]
        theme = Theme(text="purifier", category="Air", time_window="12m")
        with patch.object(patent_client_source, "is_available", return_value=True):
            items = patent_client_source.search_patents(theme, _settings())
        assert len(items) == 1


class TestFetchPatentsLive:
    @patch("sda_studio.ingestion.patent_client_source.is_available", return_value=True)
    @patch("sda_studio.ingestion.patent_client_source.search_patents")
    def test_live_patents_when_enabled(self, mock_search, _mock_available, ensure_sample_data):
        from sda_studio.domain.models import EvidenceItem

        mock_search.return_value = [
            EvidenceItem(
                source=EvidenceSource.PATENT,
                title="Live patent",
                text="Abstract",
                date=None,
                category="Air",
                region="US",
                relevance_score=0.0,
                metadata={"patent_id": "US1", "data_origin": "live"},
            )
        ]
        theme = Theme(text="air purifier", category="Air", time_window="12m")
        result = fetch_patents(_settings(), theme=theme)
        assert result.origin == DataOrigin.LIVE
        assert result.items[0].title == "Live patent"
        mock_search.assert_called_once()

    def test_csv_fallback_without_theme(self, ensure_sample_data):
        result = fetch_patents(_settings(), theme=None)
        assert result.origin == DataOrigin.SAMPLE

    @patch("sda_studio.ingestion.patent_client_source.is_available", return_value=False)
    def test_empty_when_live_enabled_but_package_missing(self, _mock_available, ensure_sample_data):
        theme = Theme(text="air purifier", category="Air", time_window="12m")
        result = fetch_patents(_settings(), theme=theme)
        assert result.origin == DataOrigin.EMPTY
        assert len(result.items) == 0


@pytest.fixture(scope="module")
def ensure_sample_data():
    from sda_studio.config.settings import SAMPLE_DIR

    if not (SAMPLE_DIR / "patents.csv").exists():
        import subprocess

        subprocess.run([sys.executable, str(ROOT / "scripts" / "generate_sample_data.py")], check=True)


class TestAnalyzeThemeWithLivePatents:
    @patch("sda_studio.ingestion.patent_client_source.is_available", return_value=True)
    @patch("sda_studio.ingestion.patent_client_source.search_patents")
    def test_analyze_theme_uses_live_patents(self, mock_search, _mock_available, ensure_sample_data):
        from sda_studio.domain.models import EvidenceItem

        mock_search.return_value = [
            EvidenceItem(
                source=EvidenceSource.PATENT,
                title="HEPA filter device",
                text="An air cleaning apparatus with HEPA filtration.",
                date=date(2024, 3, 1),
                category="Air",
                region="US",
                relevance_score=0.0,
                metadata={"patent_id": "US999", "data_origin": "live", "applicant": "TestCo"},
            )
        ]
        theme = Theme(text="hepa air purifier", category="Air", time_window="12m")
        with patch("sda_studio.storage.datasets.load_settings", return_value=_settings()):
            loaded = analyze_theme(theme)

        patent_summary = next(s for s in loaded.sources if s.source == EvidenceSource.PATENT)
        assert patent_summary.origin == DataOrigin.LIVE
        assert loaded.is_sample_data is False
