"""Product catalog connector — synthetic appliance SKU dataset or CSV fallback."""

from __future__ import annotations

import logging

import pandas as pd

from sda_studio.domain.models import EvidenceItem, EvidenceSource
from sda_studio.ingestion.catalog_sources import load_synthetic_catalog, synthetic_catalog_present
from sda_studio.ingestion.csv_loader import (
    DataOrigin,
    IngestionError,
    SourceLoadResult,
    read_validated_csv,
    resolve_csv_path,
    stamp_origin,
)
from sda_studio.config.settings import RAW_DIR
from sda_studio.config.catalog_mapping import SYNTHETIC_CATALOG_FILENAME

logger = logging.getLogger(__name__)

FILENAME = "product_catalog.csv"
REQUIRED_COLUMNS = {"product_id", "name", "brand", "category", "region", "price_usd"}


def _parse_attributes(raw) -> dict[str, str]:
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return {}
    attrs: dict[str, str] = {}
    for part in str(raw).split(";"):
        if "," in part:
            key, val = part.split(",", 1)
            attrs[key.strip()] = val.strip()
    return attrs


def _row_to_evidence(row, *, origin: DataOrigin) -> EvidenceItem:
    attrs = _parse_attributes(row.get("attributes", ""))
    attr_text = " ".join(f"{k} {v}" for k, v in attrs.items())
    price = row.get("price_usd")
    return EvidenceItem(
        source=EvidenceSource.CATALOG,
        title=str(row["name"]),
        text=attr_text,
        date=None,
        category=str(row["category"]),
        region=str(row["region"]) if row.get("region") is not None and str(row["region"]) != "nan" else None,
        relevance_score=0.0,
        metadata=stamp_origin(
            {
                "product_id": str(row["product_id"]),
                "brand": str(row["brand"]),
                "price_usd": float(price) if price is not None and str(price) != "nan" else None,
                "attributes": attrs,
                "catalog_dataset": "product_catalog_csv",
            },
            origin,
        ),
    )


def _load_catalog_csv() -> SourceLoadResult:
    path, origin = resolve_csv_path(FILENAME)
    if path is None:
        logger.warning("No product catalog CSV found in data/raw or data/sample")
        return SourceLoadResult([], DataOrigin.EMPTY, None, "catalog")

    df = read_validated_csv(path, REQUIRED_COLUMNS)

    items = [_row_to_evidence(row, origin=origin) for _, row in df.iterrows()]
    logger.info("Loaded %d catalog products from %s (%s)", len(items), path, origin.value)
    return SourceLoadResult(items, origin, path, "catalog")


def fetch_catalog() -> SourceLoadResult:
    """
    Load product catalog evidence.

    Prefers ``data/raw/appliance-skus-10k-synthetic.csv`` when present (cleaned and
    mapped to SDA categories). Otherwise uses ``product_catalog.csv``.
    """
    if synthetic_catalog_present():
        path = RAW_DIR / SYNTHETIC_CATALOG_FILENAME
        try:
            items = load_synthetic_catalog(path)
            if items:
                return SourceLoadResult(
                    items,
                    DataOrigin.USER_PROVIDED,
                    path,
                    "catalog (synthetic appliance SKUs)",
                )
            logger.warning("Synthetic catalog produced no mapped items; using CSV fallback")
        except (ValueError, OSError, pd.errors.ParserError) as exc:
            raise IngestionError(f"Could not load synthetic catalog {path}: {exc}") from exc

    return _load_catalog_csv()
