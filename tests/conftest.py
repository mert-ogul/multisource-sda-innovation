"""Shared fixtures for foundation-layer tests."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_DIR = ROOT / "data" / "sample"

sys.path.insert(0, str(ROOT / "src"))

from sda_studio.domain.models import EvidenceItem
from sda_studio.storage.datasets import load_all_evidence


@pytest.fixture(autouse=True)
def demo_only_datasets(monkeypatch, request):
    """Keep most tests on sample data unless the test module opts out."""
    if request.module.__name__ in {
        "test_review_datasets",
        "test_catalog_datasets",
        "test_real_data_mode",
    }:
        return
    monkeypatch.setattr(
        "sda_studio.storage.datasets.user_review_datasets_present",
        lambda raw_dir=None: False,
    )
    monkeypatch.setattr(
        "sda_studio.storage.datasets.synthetic_catalog_present",
        lambda raw_dir=None: False,
    )
    monkeypatch.setattr(
        "sda_studio.ingestion.reviews.user_review_datasets_present",
        lambda raw_dir=None: False,
    )
    monkeypatch.setattr(
        "sda_studio.ingestion.catalog.synthetic_catalog_present",
        lambda raw_dir=None: False,
    )


@pytest.fixture(scope="session")
def sample_evidence() -> list[EvidenceItem]:
    if not (SAMPLE_DIR / "patents.csv").exists():
        subprocess.run([sys.executable, str(ROOT / "scripts" / "generate_sample_data.py")], check=True)

    mp = pytest.MonkeyPatch()
    mp.setattr(
        "sda_studio.storage.datasets.user_review_datasets_present",
        lambda raw_dir=None: False,
    )
    mp.setattr(
        "sda_studio.storage.datasets.synthetic_catalog_present",
        lambda raw_dir=None: False,
    )
    mp.setattr(
        "sda_studio.ingestion.reviews.user_review_datasets_present",
        lambda raw_dir=None: False,
    )
    mp.setattr(
        "sda_studio.ingestion.catalog.synthetic_catalog_present",
        lambda raw_dir=None: False,
    )
    try:
        items, _, _ = load_all_evidence()
        return items
    finally:
        mp.undo()
