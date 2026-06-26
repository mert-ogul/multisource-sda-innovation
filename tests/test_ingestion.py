"""Tests for ingestion connectors and storage layer."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sda_studio.config.settings import RAW_DIR, SAMPLE_DIR
from sda_studio.domain.models import EvidenceSource
from sda_studio.ingestion.csv_loader import DataOrigin, IngestionError
from sda_studio.ingestion.catalog import fetch_catalog
from sda_studio.ingestion.news import fetch_news
from sda_studio.ingestion.patents import fetch_patents
from sda_studio.ingestion.reviews import fetch_reviews
from sda_studio.ingestion.social import fetch_social
from sda_studio.storage.datasets import load_all_evidence


@pytest.fixture(scope="module")
def ensure_sample_data():
    if not (SAMPLE_DIR / "patents.csv").exists():
        import subprocess

        subprocess.run([sys.executable, str(ROOT / "scripts" / "generate_sample_data.py")], check=True)


@pytest.fixture(autouse=True)
def use_sample_reviews_only(monkeypatch):
    """Keep ingestion tests on sample reviews.csv unless a test opts into raw datasets."""
    monkeypatch.setattr(
        "sda_studio.ingestion.reviews.user_review_datasets_present",
        lambda raw_dir=None: False,
    )
    monkeypatch.setattr(
        "sda_studio.ingestion.catalog.synthetic_catalog_present",
        lambda raw_dir=None: False,
    )


class TestIngestionSampleData:
    def test_patents_load_from_sample(self, ensure_sample_data):
        result = fetch_patents()
        assert result.is_sample
        assert result.origin == DataOrigin.SAMPLE
        assert len(result.items) > 0
        assert result.items[0].source == EvidenceSource.PATENT
        assert result.items[0].metadata["data_origin"] == "sample"

    def test_all_sources_load(self, ensure_sample_data):
        items, is_sample, summaries = load_all_evidence()
        assert len(items) > 100
        assert is_sample is True
        assert len(summaries) == 5
        assert all(s.item_count > 0 for s in summaries)
        assert all(s.origin == DataOrigin.SAMPLE for s in summaries)

    def test_each_item_has_normalized_fields(self, ensure_sample_data):
        items, _, _ = load_all_evidence()
        for item in items[:20]:
            assert item.source
            assert item.title
            assert item.category
            assert "data_origin" in item.metadata


class TestIngestionValidation:
    def test_missing_columns_raises(self, ensure_sample_data, tmp_path, monkeypatch):
        bad = tmp_path / "patents.csv"
        pd.DataFrame({"title": ["only title"]}).to_csv(bad, index=False)
        monkeypatch.setattr(
            "sda_studio.ingestion.csv_loader.RAW_DIR",
            tmp_path,
        )
        monkeypatch.setattr(
            "sda_studio.ingestion.csv_loader.SAMPLE_DIR",
            tmp_path / "empty",
        )
        with pytest.raises(IngestionError, match="missing required column"):
            fetch_patents()

    def test_empty_csv_raises(self, ensure_sample_data, tmp_path, monkeypatch):
        empty = tmp_path / "news.csv"
        pd.DataFrame(
            columns=["headline", "snippet", "source_name", "published_date", "category", "region"]
        ).to_csv(empty, index=False)
        monkeypatch.setattr("sda_studio.ingestion.csv_loader.RAW_DIR", tmp_path)
        monkeypatch.setattr("sda_studio.ingestion.csv_loader.SAMPLE_DIR", tmp_path / "none")
        with pytest.raises(IngestionError, match="no data rows"):
            fetch_news()

    def test_user_raw_preferred_over_sample(self, ensure_sample_data, tmp_path, monkeypatch):
        user_dir = tmp_path / "raw"
        user_dir.mkdir()
        sample_dir = tmp_path / "sample"
        sample_dir.mkdir()
        # valid minimal patent row
        df = pd.DataFrame(
            [{
                "patent_id": "U1",
                "title": "User patent",
                "abstract": "User abstract",
                "applicant": "UserCo",
                "filing_date": "2024-01-01",
                "category": "Air",
                "region": "US",
                "keywords": "hepa",
            }]
        )
        df.to_csv(user_dir / "patents.csv", index=False)
        monkeypatch.setattr("sda_studio.ingestion.csv_loader.RAW_DIR", user_dir)
        monkeypatch.setattr("sda_studio.ingestion.csv_loader.SAMPLE_DIR", sample_dir)
        result = fetch_patents()
        assert result.is_user_provided
        assert result.items[0].title == "User patent"
        assert result.items[0].metadata["data_origin"] == "user_provided"


class TestStorageLayer:
    def test_sample_metadata_declares_demo_mode(self, ensure_sample_data):
        import json
        from sda_studio.config.settings import SAMPLE_DIR

        meta = json.loads((SAMPLE_DIR / "metadata.json").read_text())
        assert meta["mode"] == "sample"

    def test_mixed_mode_when_raw_present(self, ensure_sample_data, tmp_path, monkeypatch):
        user_dir = tmp_path / "raw"
        user_dir.mkdir()
        pd.DataFrame(
            [{
                "product_name": "X",
                "review_text": "quiet purifier",
                "rating": 4.0,
                "review_date": "2024-06-01",
                "category": "Air",
                "region": "US",
            }]
        ).to_csv(user_dir / "reviews.csv", index=False)

        monkeypatch.setattr("sda_studio.ingestion.csv_loader.RAW_DIR", user_dir)
        monkeypatch.setattr("sda_studio.ingestion.csv_loader.SAMPLE_DIR", SAMPLE_DIR)

        items, is_sample, summaries = load_all_evidence()
        review_summary = next(s for s in summaries if s.source == EvidenceSource.REVIEW)
        assert review_summary.origin == DataOrigin.USER_PROVIDED
        assert is_sample is False
        social_summary = next(s for s in summaries if s.source == EvidenceSource.SOCIAL)
        assert social_summary.origin == DataOrigin.EMPTY
        patent_summary = next(s for s in summaries if s.source == EvidenceSource.PATENT)
        assert patent_summary.origin == DataOrigin.EMPTY
