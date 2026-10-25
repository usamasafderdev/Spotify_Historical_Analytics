from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ImportResult:
    batch_id: str
    source_name: str
    source_license: str
    chart_type: str
    country: str
    total_rows: int
    valid_rows: int
    rejected_rows: int
    duplicates_skipped: int
    rejected_details: list[str] = field(default_factory=list)


@dataclass
class ClaimMeta:
    source: str
    source_license: str
    chart_type: str
    country: str
    data_quality: str = "unknown"
    full_dataset_claim: bool = False
    notes: str = ""


@dataclass
class InventorySnapshot:
    total_streams: int
    distinct_tracks: int
    distinct_artists: int
    chart_dates_with_data: int
    coverage_percentage: float
    start_date: str | None = None
    end_date: str | None = None
    source_count: int = 0
    demo_rows: int = 0
    is_demo: bool = False
    notes: str = ""


@dataclass
class ValidationFailure:
    row_number: int
    reason: str
    raw: dict[str, Any]
