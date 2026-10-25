from __future__ import annotations

import re
import uuid
from datetime import datetime
from pathlib import Path

import pandas as pd

from .db import DatabaseManager
from .models import ImportResult


def _normalize_header(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value).lower())


def _resolve_column(columns: list[str], candidates: list[str]) -> str | None:
    normalized = { _normalize_header(column): column for column in columns }
    for candidate in candidates:
        key = _normalize_header(candidate)
        if key in normalized:
            return normalized[key]
    return None


def _as_int(value: object) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return int(value)
    text = str(value).strip()
    if not text:
        return None
    text = text.replace(",", "")
    try:
        return int(float(text))
    except ValueError:
        return None


def _parse_date(value: object) -> str | None:
    if value is None or str(value).strip() == "":
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%m/%d/%Y", "%d/%m/%Y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _as_text(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


def import_csv_file(
    db: DatabaseManager,
    csv_path: str | Path,
    source_name: str,
    source_license: str,
    chart_type: str = "daily",
    country: str = "US",
) -> ImportResult:
    return _import_dataframe(
        db,
        pd.read_csv(csv_path),
        source_name,
        source_license,
        chart_type,
        country,
        Path(csv_path).name,
    )


def import_xlsx_file(
    db: DatabaseManager,
    xlsx_path: str | Path,
    source_name: str,
    source_license: str,
    chart_type: str = "daily",
    country: str = "US",
) -> ImportResult:
    return _import_dataframe(
        db,
        pd.read_excel(xlsx_path),
        source_name,
        source_license,
        chart_type,
        country,
        Path(xlsx_path).name,
    )


def _import_dataframe(
    db: DatabaseManager,
    df: pd.DataFrame,
    source_name: str,
    source_license: str,
    chart_type: str,
    country: str,
    file_name: str,
) -> ImportResult:
    db.ensure_source(source_name, source_license, f"Imported from {file_name}")
    batch_id = db.create_batch(source_name, source_license, chart_type, country)

    columns = [str(column) for column in df.columns]
    date_col = _resolve_column(columns, ["date", "chartdate", "datevalue"])
    track_col = _resolve_column(columns, ["trackname", "track", "title", "song"])
    artist_col = _resolve_column(columns, ["artist", "artistnames", "artist_name", "artists"])
    position_col = _resolve_column(columns, ["position", "rank"])
    streams_col = _resolve_column(columns, ["streams", "stream", "totalstreams"])
    url_col = _resolve_column(columns, ["url", "uri", "spotifyid", "spotify_url"])
    region_col = _resolve_column(columns, ["region", "country", "market"])
    weekly_start_col = _resolve_column(columns, ["weeklystart", "weekstart", "week_start"])
    weekly_end_col = _resolve_column(columns, ["weeklyend", "weekend", "week_end"])
    chart_col = _resolve_column(columns, ["chart", "chartname"]) if "chart" else None

    if not all([date_col, track_col, artist_col, streams_col]):
        raise ValueError(
            "A valid CSV/XLSX file must include date, track name, artist names, and streams columns."
        )

    total_rows = 0
    valid_rows = 0
    rejected_rows = 0
    duplicates_skipped = 0
    rejected_details: list[str] = []

    for row_number, row in df.iterrows():
        total_rows += 1
        metadata = row.to_dict()
        chart_date = _parse_date(metadata.get(date_col))
        track_name = _as_text(metadata.get(track_col))
        artist_names = _as_text(metadata.get(artist_col))
        streams_value = _as_int(metadata.get(streams_col))
        region_name = _as_text(metadata.get(region_col)) if region_col else country
        position_value = _as_int(metadata.get(position_col)) if position_col else None
        original_url = _as_text(metadata.get(url_col)) if url_col else None
        weekly_start = _parse_date(metadata.get(weekly_start_col)) if weekly_start_col else None
        weekly_end = _parse_date(metadata.get(weekly_end_col)) if weekly_end_col else None
        chart_value = _as_text(metadata.get(chart_col)) if chart_col else chart_type

        if not chart_date:
            rejected_rows += 1
            rejected_details.append(f"row {row_number + 2}: invalid date")
            continue
        if not track_name or not artist_names:
            rejected_rows += 1
            rejected_details.append(f"row {row_number + 2}: missing track or artist")
            continue
        if streams_value is None or streams_value <= 0:
            rejected_rows += 1
            rejected_details.append(f"row {row_number + 2}: invalid stream count")
            continue
        if region_name and region_name.upper() != "US" and region_name.upper() != "USA" and region_name.upper() != "UNITED STATES":
            rejected_rows += 1
            rejected_details.append(f"row {row_number + 2}: non-US region {region_name}")
            continue
        if chart_value and chart_value.lower() not in {"daily", "weekly", "top200", "viral"}:
            rejected_rows += 1
            rejected_details.append(f"row {row_number + 2}: unsupported chart category")
            continue
        if chart_value and chart_type.lower() != chart_value.lower():
            rejected_rows += 1
            rejected_details.append(f"row {row_number + 2}: chart category mismatch ({chart_value} vs {chart_type})")
            continue

        track_id = _as_text(metadata.get(url_col)) if url_col else f"{track_name}|{artist_names}"
        if track_id == "":
            track_id = f"{track_name}|{artist_names}"
        if "spotify.com/track/" in track_id:
            track_id = track_id.split("spotify.com/track/")[-1].split("?")[0]

        duplicate_exists = db.connection.execute(
            "SELECT 1 FROM chart_records WHERE source = ? AND chart_type = ? AND country = ? AND chart_date = ? AND position = ? AND track_name = ? AND artist_names = ? AND streams = ? LIMIT 1",
            (source_name, chart_type, country, chart_date, position_value, track_name, artist_names, streams_value),
        ).fetchone()
        if duplicate_exists:
            duplicates_skipped += 1
            continue

        db.register_chart_record(
            batch_id=batch_id,
            source=source_name,
            source_license=source_license,
            chart_type=chart_type,
            country=country,
            chart_date=chart_date,
            weekly_start=weekly_start,
            weekly_end=weekly_end,
            position=position_value,
            track_id=track_id,
            track_name=track_name,
            artist_names=artist_names,
            streams=streams_value,
            original_url=original_url,
        )
        db.upsert_track(track_id, track_name, artist_names, source_name)
        db.upsert_artist(f"artist::{artist_names}", artist_names)
        valid_rows += 1

    result = ImportResult(
        batch_id=batch_id,
        source_name=source_name,
        source_license=source_license,
        chart_type=chart_type,
        country=country,
        total_rows=total_rows,
        valid_rows=valid_rows,
        rejected_rows=rejected_rows,
        duplicates_skipped=duplicates_skipped,
        rejected_details=rejected_details,
    )
    return result
