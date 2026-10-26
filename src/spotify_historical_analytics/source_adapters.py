from __future__ import annotations

import ast
import csv
import hashlib
import io
import re
import zipfile
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Iterator
from urllib.parse import urlparse


MGDPLUS_US_CHART_MEMBER = "charts/regional/spotify_charts_regional_us.csv"
MGDPLUS_CHART_COLUMNS = (
    "ID",
    "Track",
    "Artist",
    "Position",
    "Streams",
    "Trend",
    "Date",
    "Chart",
    "market",
)
DHRUVIL_COLUMNS = (
    "title",
    "rank",
    "date",
    "artist",
    "url",
    "region",
    "chart",
    "trend",
    "streams",
)


@dataclass(frozen=True)
class AdaptedChartRow:
    source: str
    source_file: str
    source_sha256: str
    source_row: int
    market: str | None
    chart_name: str | None
    cadence: str | None
    chart_date: str | None
    track_id: str | None
    track_name: str | None
    artist_name: str | None
    position: int | None
    streams: int | None
    trend: str | None
    artist_ids: tuple[str, ...] = ()
    error: str | None = None

    @property
    def valid(self) -> bool:
        return self.error is None


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _parse_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value.strip()).isoformat()
    except ValueError:
        return None


def _parse_integer(value: str | None) -> int | None:
    if value is None:
        return None
    normalized = value.strip()
    if not re.fullmatch(r"(?:\d+|\d{1,3}(?:,\d{3})+)", normalized):
        return None
    return int(normalized.replace(",", ""))


def _parse_mgdplus_artist_ids(value: str | None) -> tuple[str, ...] | None:
    if not value or not value.strip():
        return ()
    normalized = value.strip()
    if normalized.startswith("["):
        try:
            parsed = ast.literal_eval(normalized)
        except (SyntaxError, ValueError):
            return None
        if not isinstance(parsed, list) or not all(
            isinstance(item, str) for item in parsed
        ):
            return None
        return tuple(dict.fromkeys(item.strip() for item in parsed if item.strip()))
    return (normalized,)


def _verified_spotify_track_id(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {
        "open.spotify.com",
        "www.open.spotify.com",
    }:
        return None
    match = re.fullmatch(r"/track/([A-Za-z0-9]{22})/?", parsed.path)
    return match.group(1) if match else None


def _chunks(rows: Iterator[AdaptedChartRow], chunk_size: int) -> Iterator[list[AdaptedChartRow]]:
    if chunk_size < 1:
        raise ValueError("chunk_size must be a positive integer")
    batch: list[AdaptedChartRow] = []
    for row in rows:
        batch.append(row)
        if len(batch) == chunk_size:
            yield batch
            batch = []
    if batch:
        yield batch


def _iter_mgdplus_rows(
    archive_path: Path,
    member_name: str,
    source: str,
    archive_sha256: str,
) -> Iterator[AdaptedChartRow]:
    with zipfile.ZipFile(archive_path) as archive:
        if member_name not in archive.namelist():
            raise ValueError(f"MGD+ archive is missing the requested member: {member_name}")
        with archive.open(member_name) as binary:
            text = io.TextIOWrapper(binary, encoding="utf-8-sig", newline="")
            reader = csv.DictReader(text, delimiter="\t")
            columns = tuple(reader.fieldnames or ())
            missing = set(MGDPLUS_CHART_COLUMNS) - set(columns)
            if missing:
                raise ValueError(
                    f"MGD+ chart schema is missing columns: {', '.join(sorted(missing))}"
                )
            for source_row, raw in enumerate(reader, start=2):
                chart_date = _parse_date(raw.get("Date"))
                position = _parse_integer(raw.get("Position"))
                streams = _parse_integer(raw.get("Streams"))
                track_id = (raw.get("ID") or "").strip() or None
                market = (raw.get("market") or "").strip().upper() or None
                chart_name = (raw.get("Chart") or "").strip() or None
                error = None
                if market != "US":
                    error = "non_us_market"
                elif chart_date is None:
                    error = "invalid_chart_date"
                elif position is None or position < 1:
                    error = "invalid_chart_position"
                elif streams is None or streams < 0:
                    error = "invalid_stream_count"
                elif not track_id:
                    error = "missing_stable_track_id"
                elif not chart_name:
                    error = "missing_chart_category"
                yield AdaptedChartRow(
                    source=source,
                    source_file=f"{archive_path.name}:{member_name}",
                    source_sha256=archive_sha256,
                    source_row=source_row,
                    market=market,
                    chart_name=chart_name,
                    cadence="daily",
                    chart_date=chart_date,
                    track_id=track_id,
                    track_name=(raw.get("Track") or "").strip() or None,
                    artist_name=(raw.get("Artist") or "").strip() or None,
                    position=position,
                    streams=streams,
                    trend=(raw.get("Trend") or "").strip() or None,
                    error=error,
                )


def iter_mgdplus_us_chart_batches(
    archive_path: Path,
    *,
    source: str = "MGD+",
    member_name: str = MGDPLUS_US_CHART_MEMBER,
    chunk_size: int = 5_000,
) -> Iterator[list[AdaptedChartRow]]:
    """Read verified US chart TSV rows from a ZIP without extracting or loading it all."""
    path = Path(archive_path)
    digest = _sha256_file(path)
    yield from _chunks(_iter_mgdplus_rows(path, member_name, source, digest), chunk_size)


def iter_mgdplus_artist_mappings(
    archive_path: Path,
    member_names: tuple[str, ...],
    *,
    chunk_size: int = 5_000,
) -> Iterator[list[tuple[str, tuple[str, ...]]]]:
    """Read stable song-to-artist IDs, preserving each explicitly credited ID."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be a positive integer")
    batch: list[tuple[str, tuple[str, ...]]] = []
    with zipfile.ZipFile(archive_path) as archive:
        members = set(archive.namelist())
        for member_name in member_names:
            if member_name not in members:
                raise ValueError(f"MGD+ archive is missing metadata member: {member_name}")
            with archive.open(member_name) as binary:
                text = io.TextIOWrapper(binary, encoding="utf-8-sig", newline="")
                reader = csv.DictReader(text, delimiter="\t")
                if not {"song_id", "artist_id"}.issubset(reader.fieldnames or ()):
                    raise ValueError(
                        f"MGD+ song metadata schema in {member_name} must contain song_id and artist_id"
                    )
                for source_row, row in enumerate(reader, start=2):
                    track_id = (row.get("song_id") or "").strip()
                    artist_ids = _parse_mgdplus_artist_ids(row.get("artist_id"))
                    if not track_id:
                        raise ValueError(
                            f"MGD+ song metadata row {source_row} has no stable song_id"
                        )
                    if artist_ids is None:
                        raise ValueError(
                            f"MGD+ song metadata row {source_row} has an invalid artist_id list"
                        )
                    batch.append((track_id, artist_ids))
                    if len(batch) == chunk_size:
                        yield batch
                        batch = []
    if batch:
        yield batch


def _iter_dhruvil_rows(
    path: Path, source: str, file_sha256: str
) -> Iterator[AdaptedChartRow]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        columns = tuple(reader.fieldnames or ())
        missing = set(DHRUVIL_COLUMNS) - set(columns)
        if missing:
            raise ValueError(
                f"Dhruvil chart schema is missing columns: {', '.join(sorted(missing))}"
            )
        for source_row, raw in enumerate(reader, start=2):
            region = (raw.get("region") or "").strip()
            market = "US" if region.casefold() in {
                "us",
                "usa",
                "united states",
                "united states of america",
            } else None
            chart_name = (raw.get("chart") or "").strip() or None
            chart_date = _parse_date(raw.get("date"))
            position = _parse_integer(raw.get("rank"))
            viral = bool(chart_name and "viral" in chart_name.casefold())
            streams = None if viral else _parse_integer(raw.get("streams"))
            error = None
            if market is None:
                error = "non_us_or_unknown_region"
            elif chart_date is None:
                error = "invalid_chart_date"
            elif position is None or position < 1:
                error = "invalid_chart_position"
            elif not chart_name:
                error = "missing_chart_category"
            elif not viral and (streams is None or streams < 0):
                error = "invalid_stream_count"
            track_id = _verified_spotify_track_id(raw.get("url"))
            if error is None and track_id is None:
                error = "missing_verified_spotify_track_id"
            yield AdaptedChartRow(
                source=source,
                source_file=path.name,
                source_sha256=file_sha256,
                source_row=source_row,
                market=market,
                chart_name=chart_name,
                cadence="daily",
                chart_date=chart_date,
                track_id=track_id,
                track_name=(raw.get("title") or "").strip() or None,
                artist_name=(raw.get("artist") or "").strip() or None,
                position=position,
                streams=streams,
                trend=(raw.get("trend") or "").strip() or None,
                error=error,
            )


def iter_dhruvil_chart_batches(
    path: Path,
    *,
    source: str = "Dhruvil",
    chunk_size: int = 5_000,
) -> Iterator[list[AdaptedChartRow]]:
    """Read Dhruvil's verified CSV schema in bounded chunks; never infer cadence."""
    source_path = Path(path)
    digest = _sha256_file(source_path)
    yield from _chunks(_iter_dhruvil_rows(source_path, source, digest), chunk_size)
