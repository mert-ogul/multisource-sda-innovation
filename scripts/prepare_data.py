"""Generate sample data, validate via ingestion, and copy to data/processed/."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))

from sda_studio.config.settings import PROCESSED_DIR, RAW_DIR, SAMPLE_DIR
from sda_studio.ingestion.csv_loader import IngestionError
from sda_studio.storage.datasets import load_all_evidence

from generate_sample_data import generate_all

CSV_FILES = (
    "patents.csv",
    "news.csv",
    "reviews.csv",
    "social.csv",
    "product_catalog.csv",
)


def prepare() -> None:
    SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    if not (SAMPLE_DIR / "patents.csv").exists():
        print("Generating sample data...")
        generate_all(SAMPLE_DIR)

    for name in CSV_FILES:
        src = RAW_DIR / name if (RAW_DIR / name).exists() else SAMPLE_DIR / name
        if src.exists():
            shutil.copy2(src, PROCESSED_DIR / name)
            print(f"Copied {name} → data/processed/ (from {src.parent.name}/)")

    # Validate all sources load without error
    print("Validating ingestion...")
    try:
        items, is_sample, summaries = load_all_evidence()
    except IngestionError as exc:
        print(f"ERROR: {exc}")
        sys.exit(1)

    for summary in summaries:
        print(f"  {summary.source.value}: {summary.item_count} items — {summary.label}")

    print(f"Total: {len(items)} evidence items | sample_mode={is_sample}")
    print("Data preparation complete.")


if __name__ == "__main__":
    prepare()
