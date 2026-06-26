"""Integration tests: sample data × matching × scoring for anchor SDA themes."""

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sda_studio.config.categories import TimeWindow
from sda_studio.domain.models import Theme
from sda_studio.domain.scoring import build_opportunity_card
from sda_studio.processing.matching import match_evidence_to_theme

ANCHOR_CASES = [
    ("Air", "Silent compact air purifier for small bedrooms"),
    ("Kitchen", "Air fryer optimized for solo cooking and low energy use"),
    ("Coffee", "Easy-clean espresso machine for small kitchens"),
    ("Floor Care", "Pet-hair vacuum for small apartments with low noise at night"),
    ("Robotics", "Affordable robot vacuum with obstacle avoidance for cluttered homes"),
]


@pytest.mark.parametrize("category,theme_text", ANCHOR_CASES)
def test_anchor_theme_matches_sample_evidence(sample_evidence, category, theme_text):
    theme = Theme(
        text=theme_text,
        category=category,
        time_window=TimeWindow.ALL.value,
    )
    matched = match_evidence_to_theme(theme, sample_evidence, min_score=0.05)
    assert len(matched) >= 5, f"Expected matches for {category}: {theme_text}"
    assert all(m.category == category for m in matched)


@pytest.mark.parametrize("category,theme_text", ANCHOR_CASES[:4])  # core four product lines
def test_anchor_theme_produces_valid_opportunity_card(sample_evidence, category, theme_text):
    theme = Theme(text=theme_text, category=category, time_window=TimeWindow.ALL.value)
    matched = match_evidence_to_theme(theme, sample_evidence, min_score=0.05)
    card = build_opportunity_card(theme, matched, is_sample_data=True)

    assert card.theme_title == theme_text
    assert 0 <= card.scores.desirability <= 100
    assert 0 <= card.scores.viability <= 100
    assert 0 <= card.scores.feasibility <= 100
    assert len(card.demand_signals) >= 2
    assert len(card.supply_signals) >= 2
    assert card.scores.plain_english
