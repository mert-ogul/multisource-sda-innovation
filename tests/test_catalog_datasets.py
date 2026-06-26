"""Tests for synthetic appliance catalog ingestion."""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from sda_studio.config.settings import RAW_DIR
from sda_studio.domain.models import EvidenceSource
from sda_studio.ingestion.catalog import fetch_catalog
from sda_studio.ingestion.catalog_sources import (
    clean_energy_watts,
    clean_sku,
    load_synthetic_catalog,
    map_appliance_to_sda,
    niche_density_label,
    synthetic_catalog_present,
)
from sda_studio.ingestion.csv_loader import DataOrigin


class TestCatalogCleaning:
    def test_clean_sku_fixes_malformed_values(self):
        assert clean_sku("SKU--95743") == "SKU-95743"
        assert clean_sku("SKU77417") == "SKU-77417"
        assert clean_sku("33853") == "SKU-33853"

    def test_clean_energy_watts(self):
        assert clean_energy_watts("425W") == 425.0
        assert clean_energy_watts("415") == 415.0
        assert clean_energy_watts("0") is None
        assert clean_energy_watts(None) is None

    def test_map_appliance_to_sda(self):
        assert map_appliance_to_sda("Kettle") == "Coffee"
        assert map_appliance_to_sda("Dish Washer") == "Kitchen"
        assert map_appliance_to_sda("Toaster") == "Kitchen"

    def test_niche_density_labels(self):
        assert niche_density_label(1200) == "crowded"
        assert niche_density_label(400) == "moderate"
        assert niche_density_label(50) == "sparse"


@pytest.mark.skipif(
    not synthetic_catalog_present(),
    reason="Synthetic catalog not present in data/raw",
)
class TestSyntheticCatalogIntegration:
    def test_loads_thousands_of_skus(self):
        path = RAW_DIR / "appliance-skus-10k-synthetic.csv"
        items = load_synthetic_catalog(path)
        assert len(items) > 9000
        categories = {i.category for i in items}
        assert "Kitchen" in categories
        assert "Coffee" in categories

    def test_fetch_catalog_uses_user_dataset(self):
        result = fetch_catalog()
        assert result.origin == DataOrigin.USER_PROVIDED
        assert len(result.items) > 9000
        assert result.items[0].source == EvidenceSource.CATALOG
        assert "category_sku_total" in result.items[0].metadata
        assert result.items[0].metadata["catalog_dataset"] == "appliance_skus_10k_synthetic"

    def test_each_item_has_cleaned_fields(self):
        path = RAW_DIR / "appliance-skus-10k-synthetic.csv"
        item = load_synthetic_catalog(path)[0]
        assert item.metadata["product_id"].startswith("SKU-")
        assert item.metadata["brand"]
        assert item.metadata["appliance_type"]
