"""Clean and load the synthetic appliance SKU catalog."""

from __future__ import annotations

import logging
import re
from collections import Counter
from pathlib import Path

import pandas as pd

from sda_studio.config.catalog_mapping import (
    APPLIANCE_TYPE_TO_SDA,
    CATALOG_CROWDING_THRESHOLDS,
    SYNTHETIC_CATALOG_FILENAME,
)
from sda_studio.config.settings import RAW_DIR
from sda_studio.domain.models import EvidenceItem, EvidenceSource
from sda_studio.ingestion.csv_loader import DataOrigin, stamp_origin
from sda_studio.processing.cleaning import normalize_text

logger = logging.getLogger(__name__)

SKU_DIGITS_RE = re.compile(r"\d+")


def synthetic_catalog_present(raw_dir: Path | None = None) -> bool:
    root = raw_dir or RAW_DIR
    return (root / SYNTHETIC_CATALOG_FILENAME).exists()


def map_appliance_to_sda(appliance_type: str) -> str | None:
    key = normalize_text(appliance_type)
    if not key:
        return None
    if key in APPLIANCE_TYPE_TO_SDA:
        return APPLIANCE_TYPE_TO_SDA[key]
    for pattern, category in APPLIANCE_TYPE_TO_SDA.items():
        if pattern in key or key in pattern:
            return category
    return None


def clean_company(value) -> str:
    text = " ".join(str(value).split())
    if "/" in text:
        text = text.split("/")[0].strip()
    elif "," in text:
        text = text.split(",")[0].strip()
    return text


def clean_brand(value) -> str:
    return " ".join(str(value).split()).title()


def clean_appliance_type(value) -> str:
    text = " ".join(str(value).split()).title()
    replacements = {
        "Dish Washer": "Dishwasher",
        "Dishwasher": "Dishwasher",
    }
    return replacements.get(text, text)


def clean_sku(value) -> str:
    raw = str(value).strip().upper()
    raw = re.sub(r"SKU-+", "SKU-", raw)
    if raw.startswith("SKU") and not raw.startswith("SKU-"):
        digits = "".join(SKU_DIGITS_RE.findall(raw))
        return f"SKU-{digits}" if digits else raw
    if SKU_DIGITS_RE.fullmatch(raw):
        return f"SKU-{raw}"
    if re.fullmatch(r"SKU-\d+", raw):
        return raw
    digits = "".join(SKU_DIGITS_RE.findall(raw))
    return f"SKU-{digits}" if digits else raw


def clean_energy_watts(value) -> float | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    text = str(value).strip().upper().replace("W", "").replace(",", "")
    if not text or text in {"0", "0.0", "NAN", "NONE", "N/A"}:
        return None
    try:
        watts = float(text)
    except ValueError:
        return None
    return watts if watts > 0 else None


def niche_density_label(sku_count: int) -> str:
    if sku_count >= CATALOG_CROWDING_THRESHOLDS["crowded"]:
        return "crowded"
    if sku_count >= CATALOG_CROWDING_THRESHOLDS["moderate"]:
        return "moderate"
    return "sparse"


def load_synthetic_catalog(path: Path) -> list[EvidenceItem]:
    df = pd.read_csv(path)
    df = df.drop(columns=[c for c in df.columns if c.lower().startswith("unnamed")], errors="ignore")

    required = {"Company", "Brand", "Appliance", "Energy Consumption", "SKU"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Malformed catalog {path}: missing columns {sorted(missing)}")

    items: list[EvidenceItem] = []
    skipped = 0
    for _, row in df.iterrows():
        appliance_type = clean_appliance_type(row["Appliance"])
        category = map_appliance_to_sda(appliance_type)
        if category is None:
            skipped += 1
            continue

        brand = clean_brand(row["Brand"])
        company = clean_company(row["Company"])
        sku = clean_sku(row["SKU"])
        energy_watts = clean_energy_watts(row["Energy Consumption"])

        title = f"{brand} {appliance_type}"
        energy_text = f"{energy_watts:.0f}W" if energy_watts is not None else "unknown energy"
        text = f"{appliance_type} by {brand} ({company}). Energy consumption {energy_text}."

        items.append(
            EvidenceItem(
                source=EvidenceSource.CATALOG,
                title=title,
                text=text,
                date=None,
                category=category,
                region=None,
                relevance_score=0.0,
                metadata=stamp_origin(
                    {
                        "product_id": sku,
                        "brand": brand,
                        "company": company,
                        "appliance_type": appliance_type,
                        "energy_watts": energy_watts,
                        "catalog_dataset": "appliance_skus_10k_synthetic",
                    },
                    DataOrigin.USER_PROVIDED,
                ),
            )
        )

    category_counts = Counter(item.category for item in items)
    for item in items:
        total = category_counts[item.category]
        item.metadata["category_sku_total"] = total
        item.metadata["category_niche_density"] = niche_density_label(total)

    logger.info(
        "Loaded %d synthetic catalog SKUs from %s (%d rows skipped — unmapped appliance types)",
        len(items),
        path.name,
        skipped,
    )
    logger.info("Catalog SDA category counts: %s", dict(category_counts))
    return items
