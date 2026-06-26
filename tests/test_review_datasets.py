"""Tests for user-provided Amazon and Yelp review datasets."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sda_studio.config.settings import RAW_DIR
from sda_studio.domain.models import EvidenceSource, Theme
from sda_studio.ingestion.csv_loader import DataOrigin
from sda_studio.ingestion.review_sources import (
    load_user_review_datasets,
    user_review_datasets_present,
    _assign_sda_category,
)
from sda_studio.ingestion.reviews import fetch_reviews
from sda_studio.processing.review_insights import extract_review_insights
from sda_studio.processing.matching import match_evidence_to_theme


@pytest.mark.skipif(
    not user_review_datasets_present(),
    reason="User review datasets not present in data/raw",
)
class TestUserReviewDatasets:
    def test_datasets_detected(self):
        assert user_review_datasets_present()

    def test_loads_all_sda_categories(self):
        items = load_user_review_datasets(max_per_source=500)
        categories = {i.category for i in items}
        assert "Coffee" in categories
        assert len(items) > 1000

    def test_fetch_reviews_uses_user_data(self):
        result = fetch_reviews()
        assert result.origin == DataOrigin.USER_PROVIDED
        assert len(result.items) > 1000
        assert result.items[0].source == EvidenceSource.REVIEW
        assert "sentiment" in result.items[0].metadata
        assert "pain_points" in result.items[0].metadata

    def test_coffee_theme_matches_coffee_reviews(self):
        items = load_user_review_datasets(max_per_source=300)
        theme = Theme(
            text="easy clean quiet coffee maker",
            category="Coffee",
            time_window="All sample data",
        )
        matched = match_evidence_to_theme(theme, items)
        assert len(matched) > 0
        assert all(m.category == "Coffee" for m in matched)


class TestReviewInsights:
    def test_extracts_pain_and_desire(self):
        insights = extract_review_insights(
            "This coffee maker is loud at night and hard to clean, but I want a quiet compact machine."
        )
        assert "loud" in insights["pain_points"] or "hard" in insights["pain_points"]
        assert "quiet" in insights["desired_features"] or "compact" in insights["desired_features"]

    def test_extracts_delighters(self):
        insights = extract_review_insights("I love this espresso machine. Amazing taste and fast heating!")
        assert "love" in insights["delighters"] or "amazing" in insights["delighters"]


class TestCategoryAssignment:
    def test_robot_vacuum_maps_to_robotics(self):
        assert _assign_sda_category("iRobot Roomba robot vacuum cleaner") == "Robotics"

    def test_air_purifier_maps_to_air(self):
        assert _assign_sda_category("HEPA air purifier for bedroom") == "Air"

    def test_irrelevant_product_returns_none(self):
        assert _assign_sda_category("baby crib stroller diaper bag") is None
