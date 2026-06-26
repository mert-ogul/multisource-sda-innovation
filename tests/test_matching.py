import sys
from datetime import date, timedelta
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sda_studio.config.categories import TimeWindow
from sda_studio.domain.models import EvidenceItem, EvidenceSource, Theme
from sda_studio.processing.matching import explain_matching, match_evidence_to_theme


def _item(text: str, category: str = "Air", item_date: date | None = None) -> EvidenceItem:
    return EvidenceItem(
        source=EvidenceSource.REVIEW,
        title="Test product",
        text=text,
        date=item_date or date.today(),
        category=category,
        region="US",
        relevance_score=0.0,
    )


class TestThemeMatching:
    def test_matches_relevant_air_purifier_theme(self):
        theme = Theme(
            text="Silent compact air purifier for small bedrooms",
            category="Air",
            time_window=TimeWindow.ALL.value,
        )
        items = [
            _item("quiet hepa air purifier for small bedroom apartment"),
            _item("best espresso machine easy clean", category="Coffee"),
        ]
        matched = match_evidence_to_theme(theme, items, min_score=0.05)
        assert len(matched) >= 1
        assert matched[0].category == "Air"
        assert matched[0].relevance_score > 0

    def test_filters_wrong_category(self):
        theme = Theme(text="air fryer solo cooking", category="Kitchen", time_window=TimeWindow.ALL.value)
        items = [_item("quiet air purifier bedroom", category="Air")]
        matched = match_evidence_to_theme(theme, items)
        assert len(matched) == 0

    def test_time_window_filters_old_items(self):
        theme = Theme(text="quiet vacuum pet hair", category="Floor Care", time_window=TimeWindow.ONE_YEAR.value)
        old = _item(
            "pet hair vacuum quiet apartment",
            category="Floor Care",
            item_date=date.today() - timedelta(days=800),
        )
        recent = _item(
            "pet hair vacuum quiet apartment night",
            category="Floor Care",
            item_date=date.today() - timedelta(days=30),
        )
        matched = match_evidence_to_theme(theme, [old, recent], min_score=0.05)
        assert all(m.date and m.date >= date.today() - timedelta(days=366) for m in matched)

    def test_explain_matching_includes_theme(self):
        theme = Theme(text="test", category="Air", time_window=TimeWindow.ALL.value)
        msg = explain_matching(theme, 3)
        assert "3" in msg
        assert "Air" in msg
