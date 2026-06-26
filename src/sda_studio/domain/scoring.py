"""Transparent D-V-F scoring from matched evidence."""

from __future__ import annotations

import logging
from collections import Counter

from sda_studio.domain.models import (
    EvidenceItem,
    EvidenceSource,
    OpportunityCard,
    Recommendation,
    ScoreBreakdown,
    ScoreComponent,
    Theme,
)
from sda_studio.processing.cleaning import tokenize
from sda_studio.processing.keywords import extract_top_keywords
from sda_studio.processing.sentiment import average_sentiment

logger = logging.getLogger(__name__)

PAIN_KEYWORDS = {
    "noise", "loud", "noisy", "annoying", "bulky", "heavy", "difficult",
    "hard", "messy", "smell", "odor", "expensive", "breaks", "broken",
    "filter", "hair", "allerg", "energy", "power", "small", "compact",
    "night", "sleep", "clean", "maintenance",
}
DESIRE_KEYWORDS = {
    "quiet", "silent", "compact", "small", "efficient", "energy",
    "easy", "simple", "affordable", "portable", "lightweight", "smart",
    "auto", "self-clean", "hepa", "cordless", "solo", "apartment",
}


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _pain_desire_counts(items: list[EvidenceItem]) -> tuple[int, int]:
    pain = desire = 0
    for item in items:
        words = set(tokenize(f"{item.title} {item.text}"))
        pain += len(words & PAIN_KEYWORDS)
        desire += len(words & DESIRE_KEYWORDS)
    return pain, desire


def _patent_crowding(patents: list[EvidenceItem]) -> float:
    if not patents:
        return 0.0
    applicants = [p.metadata.get("applicant", "unknown") for p in patents]
    counts = Counter(applicants)
    top_share = counts.most_common(1)[0][1] / len(patents) if patents else 0
    volume_factor = min(len(patents) / 20.0, 1.0)
    return _clamp((volume_factor * 0.6 + top_share * 0.4) * 100)


def compute_scores(evidence: list[EvidenceItem]) -> ScoreBreakdown:
    """Compute Desirability, Viability, Feasibility from evidence buckets."""
    by_source: dict[EvidenceSource, list[EvidenceItem]] = {}
    for item in evidence:
        by_source.setdefault(item.source, []).append(item)

    reviews = by_source.get(EvidenceSource.REVIEW, [])
    social = by_source.get(EvidenceSource.SOCIAL, [])
    news = by_source.get(EvidenceSource.NEWS, [])
    patents = by_source.get(EvidenceSource.PATENT, [])
    catalog = by_source.get(EvidenceSource.CATALOG, [])

    user_text = reviews + social
    pain_count, desire_count = _pain_desire_counts(user_text)
    user_sentiment = average_sentiment([e.text for e in user_text]) if user_text else 0.0

    pain_signal = min(pain_count / 5.0, 1.0) * 35
    desire_signal = min(desire_count / 5.0, 1.0) * 35
    sentiment_signal = _clamp((-user_sentiment + 1) / 2 * 30) if user_text else 15
    desirability = _clamp(pain_signal + desire_signal + sentiment_signal)

    news_signal = min(len(news) / 8.0, 1.0) * 40
    catalog_signal = min(len(catalog) / 10.0, 1.0) * 35
    entity_richness = min(
        sum(len(e.metadata.get("entities", [])) for e in news) / 10.0, 1.0
    ) * 25
    viability = _clamp(news_signal + catalog_signal + entity_richness)

    patent_maturity = min(len(patents) / 12.0, 1.0) * 50
    crowdedness = _patent_crowding(patents)
    crowding_penalty = crowdedness * 0.35
    catalog_maturity = min(len(catalog) / 8.0, 1.0) * 30
    feasibility = _clamp(patent_maturity + catalog_maturity - crowding_penalty + 20)

    components = [
        ScoreComponent("Pain-point mentions", pain_signal, 0.35, f"{pain_count} pain-related term hits in reviews/social"),
        ScoreComponent("Desired-feature mentions", desire_signal, 0.35, f"{desire_count} desire-related term hits"),
        ScoreComponent("User sentiment (negative → opportunity)", sentiment_signal, 0.30, f"Avg sentiment {user_sentiment:.2f}"),
        ScoreComponent("News coverage", news_signal, 0.40, f"{len(news)} matched articles"),
        ScoreComponent("Catalog coverage", catalog_signal, 0.35, f"{len(catalog)} matched products"),
        ScoreComponent("Market entities in news", entity_richness, 0.25, "Companies/products mentioned in news"),
        ScoreComponent("Patent technical maturity", patent_maturity, 0.50, f"{len(patents)} relevant patents"),
        ScoreComponent("Patent crowding (reduces feasibility)", -crowding_penalty, 0.35, f"Crowdedness index {crowdedness:.0f}/100"),
        ScoreComponent("Product catalog maturity", catalog_maturity, 0.30, "Existing products show deployable tech"),
    ]

    plain = (
        f"Desirability ({desirability:.0f}) reflects user pain and desired features in "
        f"{len(user_text)} review/social items, with sentiment factored in. "
        f"Viability ({viability:.0f}) rises with {len(news)} news hits and {len(catalog)} catalog products. "
        f"Feasibility ({feasibility:.0f}) benefits from {len(patents)} patents and catalog maturity, "
        f"adjusted down by patent crowdedness ({crowdedness:.0f}/100 — shown as a signal, not automatically bad)."
    )

    return ScoreBreakdown(
        desirability=desirability,
        viability=viability,
        feasibility=feasibility,
        crowdedness=crowdedness,
        components=components,
        plain_english=plain,
    )


def _recommendation(scores: ScoreBreakdown) -> Recommendation:
    avg = (scores.desirability + scores.viability + scores.feasibility) / 3
    if avg >= 60 and scores.desirability >= 55:
        return Recommendation.EXPLORE
    if avg >= 45:
        return Recommendation.WATCH
    return Recommendation.DEPRIORITIZE


def _demand_signals(evidence: list[EvidenceItem]) -> list[str]:
    user_items = [e for e in evidence if e.source in (EvidenceSource.REVIEW, EvidenceSource.SOCIAL)]
    keywords = extract_top_keywords([e.text for e in user_items], top_n=8)
    pain, desire = _pain_desire_counts(user_items)
    signals: list[str] = []
    if pain > 0:
        signals.append(f"Recurring user pain themes ({pain} keyword hits) around noise, size, cleaning, and energy use")
    if desire > 0:
        signals.append(f"Frequent desired-feature language ({desire} hits) — quiet, compact, efficient, easy-clean")
    if keywords:
        signals.append(f"Top discussion topics: {', '.join(keywords[:5])}")
    social = [e for e in evidence if e.source == EvidenceSource.SOCIAL]
    if social:
        avg_engagement = sum(e.metadata.get("upvotes", 0) for e in social) / len(social)
        signals.append(f"Social engagement avg {avg_engagement:.0f} upvotes on matched posts")
    while len(signals) < 2:
        signals.append("Moderate user-voice evidence in sample data for this theme")
    return signals[:4]


def _supply_signals(evidence: list[EvidenceItem]) -> list[str]:
    patents = [e for e in evidence if e.source == EvidenceSource.PATENT]
    news = [e for e in evidence if e.source == EvidenceSource.NEWS]
    catalog = [e for e in evidence if e.source == EvidenceSource.CATALOG]
    signals: list[str] = []
    if patents:
        applicants = Counter(p.metadata.get("applicant", "?") for p in patents).most_common(3)
        top = ", ".join(f"{a} ({c})" for a, c in applicants)
        signals.append(f"{len(patents)} patent filings; top applicants: {top}")
    if news:
        signals.append(f"{len(news)} news articles signaling market and product activity")
    if catalog:
        brands = Counter(c.metadata.get("brand", "?") for c in catalog).most_common(3)
        brand_str = ", ".join(f"{b} ({n})" for b, n in brands)
        niche = catalog[0].metadata.get("category_niche_density")
        total = catalog[0].metadata.get("category_sku_total")
        if niche and total:
            signals.append(
                f"{len(catalog)} theme-matched catalog SKUs; "
                f"{total} total in category ({niche} niche)"
            )
        else:
            signals.append(f"{len(catalog)} catalog products; brands: {brand_str}")
    crowdedness = _patent_crowding(patents)
    signals.append(f"Patent crowdedness index: {crowdedness:.0f}/100 (competitive intensity signal)")
    return signals[:4]


def build_opportunity_card(
    theme: Theme,
    evidence: list[EvidenceItem],
    *,
    is_sample_data: bool,
) -> OpportunityCard:
    """Assemble a full opportunity card from theme and matched evidence."""
    scores = compute_scores(evidence)
    recommendation = _recommendation(scores)
    snippets = sorted(evidence, key=lambda e: e.relevance_score, reverse=True)[:8]

    return OpportunityCard(
        theme_title=theme.text,
        category=theme.category,
        demand_signals=_demand_signals(evidence),
        supply_signals=_supply_signals(evidence),
        scores=scores,
        recommendation=recommendation,
        evidence_snippets=snippets,
        is_sample_data=is_sample_data,
        region=theme.region,
    )
