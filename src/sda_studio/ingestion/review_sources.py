"""Load user-provided review datasets from data/raw."""

from __future__ import annotations

import csv
import logging
import re
from datetime import date
from pathlib import Path

import pandas as pd

from sda_studio.config.review_keywords import (
    AMAZON_CATEGORY_HINTS,
    SDA_CATEGORY_KEYWORDS,
    USER_REVIEW_DATASETS,
)
from sda_studio.config.settings import RAW_DIR
from sda_studio.domain.models import EvidenceItem, EvidenceSource
from sda_studio.ingestion.csv_loader import DataOrigin, stamp_origin
from sda_studio.processing.cleaning import normalize_text
from sda_studio.processing.review_insights import extract_review_insights

logger = logging.getLogger(__name__)

STAR_RATING_RE = re.compile(r"(\d+(?:\.\d+)?)")
YELP_DATE_RE = re.compile(r"\b(\d{1,2}/\d{1,2}/\d{4})\b")


def user_review_datasets_present(raw_dir: Path | None = None) -> bool:
    root = raw_dir or RAW_DIR
    return any((root / name).exists() for name in USER_REVIEW_DATASETS)


def _parse_rating(value) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value)
    match = STAR_RATING_RE.search(text)
    if match:
        try:
            return float(match.group(1))
        except ValueError:
            return None
    try:
        return float(text)
    except ValueError:
        return None


def _parse_flexible_date(value) -> date | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return pd.to_datetime(value).date()
    except (ValueError, TypeError):
        return None


def _parse_yelp_date(text: str) -> date | None:
    match = YELP_DATE_RE.search(text or "")
    if not match:
        return None
    try:
        return pd.to_datetime(match.group(1), format="%m/%d/%Y").date()
    except (ValueError, TypeError):
        return None


def _assign_sda_category(blob: str, product_category: str | None = None) -> str | None:
    normalized = normalize_text(blob)
    product_cat = normalize_text(product_category or "")

    for category, keywords in SDA_CATEGORY_KEYWORDS.items():
        hints = AMAZON_CATEGORY_HINTS.get(category, [])
        category_hint = any(hint in product_cat for hint in hints) if product_cat else True
        if not category_hint and category in {"Kitchen", "Coffee", "Air", "Floor Care", "Robotics"}:
            # For Amazon, require category hint OR a strong product-title match.
            title_only = normalized[:200]
            if not any(kw in title_only for kw in keywords[:3]):
                continue
        if any(kw in normalized for kw in keywords):
            return category
    return None


def _build_review_item(
    *,
    product_name: str,
    review_text: str,
    rating: float | None,
    review_date: date | None,
    category: str,
    region: str | None,
    dataset: str,
    extra_metadata: dict | None = None,
) -> EvidenceItem | None:
    text = (review_text or "").strip()
    if not text:
        return None

    insights = extract_review_insights(text)
    metadata = {
        "rating": rating,
        "sentiment": insights["sentiment"],
        "pain_points": insights["pain_points"],
        "desired_features": insights["desired_features"],
        "delighters": insights["delighters"],
        "topics": insights["topics"],
        "review_dataset": dataset,
    }
    if extra_metadata:
        metadata.update(extra_metadata)

    return EvidenceItem(
        source=EvidenceSource.REVIEW,
        title=product_name.strip() or "Product review",
        text=text,
        date=review_date,
        category=category,
        region=region,
        relevance_score=0.0,
        metadata=stamp_origin(metadata, DataOrigin.USER_PROVIDED),
    )


def load_coffee_maker_reviews(path: Path) -> list[EvidenceItem]:
    df = pd.read_csv(path)
    items: list[EvidenceItem] = []
    for _, row in df.iterrows():
        item = _build_review_item(
            product_name="Amazon coffee maker",
            review_text=str(row.get("review", "")),
            rating=_parse_rating(row.get("rating")),
            review_date=_parse_flexible_date(row.get("review_date")),
            category="Coffee",
            region="US",
            dataset="coffee_maker",
            extra_metadata={"reviewer": str(row.get("handle", ""))},
        )
        if item:
            items.append(item)
    logger.info("Loaded %d coffee maker reviews from %s", len(items), path.name)
    return items


def load_yelp_reviews(path: Path) -> list[EvidenceItem]:
    """Load Yelp coffee-shop reviews (raw or ratings_and_sentiments)."""
    encoding = "utf-8"
    try:
        df = pd.read_csv(path, encoding=encoding)
    except UnicodeDecodeError:
        df = pd.read_csv(path, encoding="latin-1")

    text_col = "review_text" if "review_text" in df.columns else "full_review_text"
    items: list[EvidenceItem] = []
    for _, row in df.iterrows():
        review_text = str(row.get(text_col, ""))
        shop = str(row.get("coffee_shop_name", "Austin coffee shop")).strip()
        rating = _parse_rating(row.get("rating") or row.get("star_rating"))
        review_date = _parse_yelp_date(review_text)

        attr_sentiments = {}
        for col in df.columns:
            if col.endswith("_sent") and col not in {"overall_sent"}:
                val = row.get(col)
                if val is not None and str(val) != "nan":
                    attr_sentiments[col.replace("_sent", "")] = val

        item = _build_review_item(
            product_name=shop,
            review_text=review_text,
            rating=rating,
            review_date=review_date,
            category="Coffee",
            region="US",
            dataset=path.stem,
            extra_metadata={
                "source_name": "Yelp",
                "attribute_sentiments": attr_sentiments,
                "overall_sentiment_score": row.get("overall_sent"),
            },
        )
        if item:
            items.append(item)
    logger.info("Loaded %d Yelp coffee reviews from %s", len(items), path.name)
    return items


def load_amazon_reviews(path: Path) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    with path.open(encoding="utf-8", errors="replace") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        for row in reader:
            title = (row.get("PRODUCT_TITLE") or "").strip().strip('"')
            text = (row.get("REVIEW_TEXT") or "").strip()
            product_category = (row.get("PRODUCT_CATEGORY") or "").strip()
            blob = f"{product_category} {title} {text}"
            category = _assign_sda_category(blob, product_category)
            if category is None:
                continue

            item = _build_review_item(
                product_name=title or "Amazon product",
                review_text=text,
                rating=_parse_rating(row.get("RATING")),
                review_date=None,
                category=category,
                region="US",
                dataset="amazon_reviews",
                extra_metadata={
                    "source_name": "Amazon",
                    "product_category": product_category,
                    "product_id": row.get("PRODUCT_ID"),
                    "verified_purchase": row.get("VERIFIED_PURCHASE"),
                },
            )
            if item:
                items.append(item)

    logger.info("Loaded %d SDA-filtered Amazon reviews from %s", len(items), path.name)
    return items


def _dedupe_items(items: list[EvidenceItem]) -> list[EvidenceItem]:
    seen: set[tuple[str, str, str]] = set()
    unique: list[EvidenceItem] = []
    for item in items:
        key = (item.title, item.text[:120], item.category)
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def load_user_review_datasets(
    raw_dir: Path | None = None,
    *,
    max_per_source: int | None = None,
) -> list[EvidenceItem]:
    """Load and merge all user review datasets under data/raw."""
    root = raw_dir or RAW_DIR
    items: list[EvidenceItem] = []

    coffee_path = root / "coffee_maker.csv"
    if coffee_path.exists():
        batch = load_coffee_maker_reviews(coffee_path)
        if max_per_source:
            batch = batch[:max_per_source]
        items.extend(batch)

    yelp_path = root / "ratings_and_sentiments.csv"
    if not yelp_path.exists():
        yelp_path = root / "raw_yelp_review_data.csv"
    if yelp_path.exists():
        batch = load_yelp_reviews(yelp_path)
        if max_per_source:
            batch = batch[:max_per_source]
        items.extend(batch)

    amazon_path = root / "amazon_reviews.txt"
    if amazon_path.exists():
        batch = load_amazon_reviews(amazon_path)
        if max_per_source:
            batch = batch[:max_per_source]
        items.extend(batch)

    items = _dedupe_items(items)
    logger.info("Loaded %d total user review evidence items", len(items))
    return items
