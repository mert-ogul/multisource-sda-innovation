"""CSV loading, validation, and provenance for ingestion connectors."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from enum import Enum
from pathlib import Path

import pandas as pd

from sda_studio.config.settings import RAW_DIR, SAMPLE_DIR
from sda_studio.domain.models import EvidenceItem


class DataOrigin(str, Enum):
    SAMPLE = "sample"
    USER_PROVIDED = "user_provided"
    LIVE = "live"
    EMPTY = "empty"


@dataclass(frozen=True)
class SourceLoadResult:
    """Outcome of loading one evidence source."""

    items: list[EvidenceItem]
    origin: DataOrigin
    path: Path | None
    source_name: str

    @property
    def is_sample(self) -> bool:
        return self.origin == DataOrigin.SAMPLE

    @property
    def is_user_provided(self) -> bool:
        return self.origin == DataOrigin.USER_PROVIDED

    @property
    def is_live(self) -> bool:
        return self.origin == DataOrigin.LIVE

    @property
    def label(self) -> str:
        if self.origin == DataOrigin.SAMPLE:
            return f"Sample/demo data ({self.source_name})"
        if self.origin == DataOrigin.USER_PROVIDED:
            return f"User-provided data ({self.source_name})"
        if self.origin == DataOrigin.LIVE:
            return f"Live API data ({self.source_name})"
        return f"No data loaded ({self.source_name})"


class IngestionError(Exception):
    """Raised when a CSV exists but cannot be parsed or is missing required columns."""


def parse_date(value, *, field_name: str, row_index: int, file_path: Path) -> date | None:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    try:
        return pd.to_datetime(value).date()
    except (ValueError, TypeError) as exc:
        raise IngestionError(
            f"Invalid date in '{field_name}' at row {row_index} of {file_path}: {value!r}"
        ) from exc


def require_columns(df: pd.DataFrame, required: set[str], file_path: Path) -> None:
    missing = required - set(df.columns)
    if missing:
        raise IngestionError(
            f"Malformed CSV {file_path}: missing required column(s): {', '.join(sorted(missing))}. "
            f"Expected columns include: {', '.join(sorted(required))}."
        )


def load_csv(path: Path) -> pd.DataFrame:
    try:
        return pd.read_csv(path)
    except pd.errors.EmptyDataError as exc:
        raise IngestionError(f"Malformed CSV {path}: file is empty.") from exc
    except (OSError, pd.errors.ParserError, UnicodeDecodeError) as exc:
        raise IngestionError(f"Could not read CSV {path}: {exc}") from exc


def read_validated_csv(path: Path, required_columns: set[str]) -> pd.DataFrame:
    """Load a CSV and fail loudly if it is empty or missing required columns."""
    df = load_csv(path)
    if df.empty:
        raise IngestionError(f"Malformed CSV {path}: no data rows after header.")
    require_columns(df, required_columns, path)
    return df


def resolve_csv_path(filename: str) -> tuple[Path | None, DataOrigin]:
    """Prefer user-provided raw data over sample data."""
    raw_path = RAW_DIR / filename
    if raw_path.exists():
        return raw_path, DataOrigin.USER_PROVIDED
    sample_path = SAMPLE_DIR / filename
    if sample_path.exists():
        return sample_path, DataOrigin.SAMPLE
    return None, DataOrigin.EMPTY


def stamp_origin(metadata: dict, origin: DataOrigin) -> dict:
    """Attach provenance to item metadata."""
    out = dict(metadata)
    out["data_origin"] = origin.value
    return out
