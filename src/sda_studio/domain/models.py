"""Domain models for evidence, themes, and opportunity cards."""

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any


class EvidenceSource(str, Enum):
    PATENT = "patent"
    NEWS = "news"
    REVIEW = "review"
    SOCIAL = "social"
    CATALOG = "catalog"


class Recommendation(str, Enum):
    EXPLORE = "Explore"
    WATCH = "Watch"
    DEPRIORITIZE = "Deprioritize"


@dataclass(frozen=True)
class Theme:
    text: str
    category: str
    time_window: str
    region: str | None = None


@dataclass
class EvidenceItem:
    source: EvidenceSource
    title: str
    text: str
    date: date | None
    category: str
    region: str | None
    relevance_score: float
    metadata: dict[str, Any] = field(default_factory=dict)
    match_explanation: str = ""


@dataclass
class PatentSignal:
    patent_id: str
    title: str
    abstract: str
    applicant: str
    filing_date: date | None
    category: str
    region: str | None
    keywords: list[str] = field(default_factory=list)


@dataclass
class NewsSignal:
    headline: str
    snippet: str
    source_name: str
    published_date: date | None
    category: str
    region: str | None
    entities: list[str] = field(default_factory=list)


@dataclass
class ReviewSignal:
    product_name: str
    review_text: str
    rating: float | None
    review_date: date | None
    category: str
    region: str | None
    sentiment: float | None = None


@dataclass
class SocialSignal:
    title: str
    body: str
    platform: str
    posted_date: date | None
    category: str
    region: str | None
    upvotes: int = 0
    comment_count: int = 0
    sentiment: float | None = None


@dataclass
class ProductItem:
    product_id: str
    name: str
    brand: str
    category: str
    region: str | None
    price_usd: float | None
    attributes: dict[str, str] = field(default_factory=dict)


@dataclass
class ScoreComponent:
    name: str
    value: float
    weight: float
    explanation: str


@dataclass
class ScoreBreakdown:
    desirability: float
    viability: float
    feasibility: float
    crowdedness: float
    components: list[ScoreComponent] = field(default_factory=list)
    plain_english: str = ""


@dataclass
class OpportunityCard:
    theme_title: str
    category: str
    demand_signals: list[str]
    supply_signals: list[str]
    scores: ScoreBreakdown
    recommendation: Recommendation
    evidence_snippets: list[EvidenceItem]
    is_sample_data: bool
    region: str | None = None
