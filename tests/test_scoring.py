import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sda_studio.domain.models import EvidenceItem, EvidenceSource, Theme
from sda_studio.domain.scoring import build_opportunity_card, compute_scores


def _review(text: str) -> EvidenceItem:
    return EvidenceItem(
        source=EvidenceSource.REVIEW,
        title="Product",
        text=text,
        date=None,
        category="Air",
        region="US",
        relevance_score=0.5,
        metadata={"sentiment": -0.3},
    )


class TestScoring:
    def test_desirability_rises_with_pain_points(self):
        low = compute_scores([])
        high = compute_scores(
            [
                _review("too loud at night noisy filter expensive"),
                _review("need quiet compact hepa for bedroom"),
            ],
        )
        assert high.desirability > low.desirability

    def test_scores_bounded_0_100(self):
        scores = compute_scores([_review("noise quiet hepa")])
        assert 0 <= scores.desirability <= 100
        assert 0 <= scores.viability <= 100
        assert 0 <= scores.feasibility <= 100

    def test_opportunity_card_structure(self):
        theme = Theme(text="quiet air purifier bedroom", category="Air", time_window="All sample data")
        items = [
            EvidenceItem(EvidenceSource.REVIEW, "P", "noisy loud filter allergy bedroom quiet", None, "Air", "US", 0.5),
            EvidenceItem(EvidenceSource.SOCIAL, "Q", "best quiet purifier apartment hepa", None, "Air", "US", 0.5, {"upvotes": 100}),
            EvidenceItem(EvidenceSource.NEWS, "N", "Philips launches quiet purifier", None, "Air", "EU", 0.5, {"entities": ["Philips"]}),
            EvidenceItem(EvidenceSource.PATENT, "Pat", "hepa quiet fan compact", None, "Air", "EU", 0.5, {"applicant": "Philips"}),
            EvidenceItem(EvidenceSource.CATALOG, "C", "hepa quiet", None, "Air", "EU", 0.5, {"brand": "Philips"}),
        ]
        card = build_opportunity_card(theme, items, is_sample_data=True)
        assert len(card.demand_signals) >= 2
        assert len(card.supply_signals) >= 2
        assert card.recommendation.value in ("Explore", "Watch", "Deprioritize")
