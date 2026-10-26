from __future__ import annotations

import argparse
import csv
import io
import json
import re
import sqlite3
import sys
import zipfile
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Iterable, Mapping, Sequence

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from spotify_historical_analytics.research_pipeline import (  # noqa: E402
    DATASETS,
    sha256_file,
)


US_CHART_MEMBER = "charts/regional/spotify_charts_regional_us.csv"


def _unsafe_member_name(name: str) -> bool:
    path = PurePosixPath(name)
    windows_path = PureWindowsPath(name)
    return (
        path.is_absolute()
        or ".." in path.parts
        or windows_path.is_absolute()
        or ".." in windows_path.parts
        or bool(windows_path.drive)
    )


def _parse_streams(value: str | None) -> int | None:
    if value is None:
        return None
    normalized = value.strip()
    if not re.fullmatch(r"(?:\d+|\d{1,3}(?:,\d{3})+)", normalized):
        return None
    return int(normalized.replace(",", ""))


def _write_csv(
    path: Path,
    fields: Sequence[str],
    records: Iterable[Mapping[str, Any]],
) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)


def _cross_source_comparison(
    database_path: Path,
    dataset_id: str,
    dataset_version: int,
    zenodo_observations: Mapping[tuple[str, str, int], set[int]],
) -> dict[str, Any]:
    database_uri = f"{database_path.resolve().as_uri()}?mode=ro"
    connection = sqlite3.connect(database_uri, uri=True)
    try:
        dhruvil: dict[tuple[str, str, int], set[int]] = defaultdict(set)
        for chart_date, track_id, position, streams in connection.execute(
            """
            SELECT o.chart_date, o.track_id, o.position, o.streams
            FROM staged_observations o
            JOIN staged_files f USING (dataset_id, dataset_version, file_sha256)
            WHERE f.status='complete' AND o.dataset_id=? AND o.dataset_version=?
              AND o.category='songs' AND o.cadence='daily' AND o.country='US'
              AND lower(replace(replace(COALESCE(o.chart_name, ''), ' ', ''), '-', ''))='top200'
              AND o.track_id IS NOT NULL AND o.streams IS NOT NULL
            """,
            (dataset_id, dataset_version),
        ):
            dhruvil[(chart_date, track_id, int(position))].add(int(streams))
        shared = dhruvil.keys() & zenodo_observations.keys()
        exact = sum(
            1
            for key in shared
            if len(dhruvil[key]) == 1
            and len(zenodo_observations[key]) == 1
            and dhruvil[key] == zenodo_observations[key]
        )
        conflicts = len(shared) - exact
        dhruvil_dates = [key[0] for key in dhruvil]
        first_dhruvil_date = min(dhruvil_dates) if dhruvil_dates else None
        last_dhruvil_date = max(dhruvil_dates) if dhruvil_dates else None
        mgd_in_dhruvil_span = {
            key: streams
            for key, streams in zenodo_observations.items()
            if first_dhruvil_date is not None
            and last_dhruvil_date is not None
            and first_dhruvil_date <= key[0] <= last_dhruvil_date
        }
        by_year: list[dict[str, Any]] = []
        years = sorted({key[0][:4] for key in dhruvil} | {key[0][:4] for key in zenodo_observations})
        for year in years:
            dhruvil_year = {key: value for key, value in dhruvil.items() if key[0].startswith(year)}
            mgd_year = {
                key: value
                for key, value in zenodo_observations.items()
                if key[0].startswith(year)
            }
            common_year = dhruvil_year.keys() & mgd_year.keys()
            same_year = sum(
                1
                for key in common_year
                if len(dhruvil_year[key]) == 1
                and len(mgd_year[key]) == 1
                and dhruvil_year[key] == mgd_year[key]
            )
            by_year.append(
                {
                    "year": year,
                    "dhruvil_unique_keys": len(dhruvil_year),
                    "mgdplus_unique_keys": len(mgd_year),
                    "shared_keys": len(common_year),
                    "same_stream_keys": same_year,
                    "different_or_ambiguous_stream_keys": len(common_year) - same_year,
                }
            )
        return {
            "comparison_source": f"{dataset_id}@{dataset_version}",
            "matching_fields": ["chart_date", "track_id", "position"],
            "dhruvil_date_span": [first_dhruvil_date, last_dhruvil_date],
            "dhruvil_unique_top200_keys": len(dhruvil),
            "mgdplus_unique_top200_keys": len(zenodo_observations),
            "mgdplus_unique_keys_in_dhruvil_date_span": len(mgd_in_dhruvil_span),
            "shared_keys": len(shared),
            "dhruvil_only_keys_in_comparison_span": len(dhruvil.keys() - mgd_in_dhruvil_span.keys()),
            "mgdplus_only_keys_in_comparison_span": len(mgd_in_dhruvil_span.keys() - dhruvil.keys()),
            "same_stream_keys": exact,
            "different_or_ambiguous_stream_keys": conflicts,
            "by_year": by_year,
            "not_a_source_precedence_decision": True,
            "note": (
                "Rows were compared by matching date, track ID, and rank only. "
                "Neither source was selected as authoritative; discrepancies are not resolved."
            ),
        }
    finally:
        connection.close()


def audit_archive(
    archive_path: Path,
    report_dir: Path,
    *,
    compact_database: Path | None = None,
    dataset_id: str = "dhruvildave/spotify-charts",
    dataset_version: int = 85,
    start_year: int = 2017,
    end_year: int = 2026,
) -> dict[str, Any]:
    archive_path = archive_path.resolve()
    report_dir = report_dir.resolve()
    if not archive_path.is_file():
        raise FileNotFoundError(archive_path)
    if report_dir.exists():
        raise FileExistsError(f"Refusing to overwrite report directory: {report_dir}")
    if start_year > end_year:
        raise ValueError("start_year must not exceed end_year")
    report_dir.mkdir(parents=True)

    with zipfile.ZipFile(archive_path) as archive:
        bad_member = archive.testzip()
        if bad_member is not None:
            raise zipfile.BadZipFile(f"CRC failed for archive member: {bad_member}")
        members = [item for item in archive.infolist() if not item.is_dir()]
        all_region_members = [
            item.filename
            for item in members
            if item.filename.startswith("charts/regional/spotify_charts_regional_")
            and item.filename.casefold().endswith(".csv")
            and ".ipynb_checkpoints/" not in item.filename.casefold()
        ]
        region_codes = sorted(
            {
                item.rsplit("_", 1)[-1][:-4].casefold()
                for item in all_region_members
            }
        )
        song_metadata_members = sorted(
            item.filename
            for item in members
            if item.filename.startswith("songs/regional/us/")
            and item.filename.casefold().endswith(".csv")
        )
        artist_metadata_members = sorted(
            item.filename
            for item in members
            if item.filename.startswith("artists/us/")
            and item.filename.casefold().endswith(".csv")
        )
        member_records = [
            {
                "name": item.filename,
                "size_bytes": item.file_size,
                "compressed_bytes": item.compress_size,
                "compression": item.compress_type,
                "crc32": f"{item.CRC:08x}",
                "is_unsafe_path": _unsafe_member_name(item.filename),
            }
            for item in members
        ]
        _write_csv(
            report_dir / "zenodo_mgdplus_archive_members.csv",
            (
                "name",
                "size_bytes",
                "compressed_bytes",
                "compression",
                "crc32",
                "is_unsafe_path",
            ),
            member_records,
        )
        chart_info = archive.getinfo(US_CHART_MEMBER)
        chart_counts: Counter[str] = Counter()
        market_counts: Counter[str] = Counter()
        rows_by_date: Counter[str] = Counter()
        identity_counts: Counter[tuple[str, str, int]] = Counter()
        streams_by_date_chart_position: dict[tuple[str, str, int], set[int]] = {}
        unique_ids: set[str] = set()
        id_lengths: Counter[int] = Counter()
        stream_missing = stream_invalid = rank_invalid = date_invalid = 0
        rank_values: list[int] = []
        id_missing = 0
        row_count = 0

        with archive.open(chart_info) as binary:
            text = io.TextIOWrapper(binary, encoding="utf-8-sig", newline="")
            reader = csv.DictReader(text, delimiter="\t")
            headers = reader.fieldnames or []
            required_headers = {"ID", "Position", "Streams", "Date", "Chart", "market"}
            missing_headers = sorted(required_headers - set(headers))
            if missing_headers:
                raise ValueError(
                    f"MGD+ US chart file is missing required fields: {missing_headers}"
                )
            for row in reader:
                row_count += 1
                chart = (row.get("Chart") or "").strip()
                market = (row.get("market") or "").strip()
                chart_counts[chart] += 1
                market_counts[market] += 1

                raw_date = (row.get("Date") or "").strip()
                try:
                    chart_day = date.fromisoformat(raw_date)
                except ValueError:
                    date_invalid += 1
                    continue
                chart_date = chart_day.isoformat()
                rows_by_date[chart_date] += 1

                raw_id = (row.get("ID") or "").strip()
                if raw_id:
                    unique_ids.add(raw_id)
                    id_lengths[len(raw_id)] += 1
                else:
                    id_missing += 1
                raw_streams = (row.get("Streams") or "").strip()
                streams = _parse_streams(raw_streams)
                if not raw_streams:
                    stream_missing += 1
                elif streams is None:
                    stream_invalid += 1
                try:
                    position = int((row.get("Position") or "").strip())
                    rank_values.append(position)
                except ValueError:
                    rank_invalid += 1
                    continue
                if raw_id:
                    key = (chart_date, raw_id, position)
                    identity_counts[key] += 1
                    if streams is not None:
                        streams_by_date_chart_position.setdefault(key, set()).add(streams)

        metadata_schemas: dict[str, list[str]] = {}
        for member_name in [*song_metadata_members, *artist_metadata_members]:
            with archive.open(member_name) as binary:
                text = io.TextIOWrapper(binary, encoding="utf-8-sig", newline="")
                metadata_schemas[member_name] = next(
                    csv.reader(text, delimiter="\t"), []
                )

        duplicate_groups = sum(1 for count in identity_counts.values() if count > 1)
        duplicate_extra_rows = sum(
            count - 1 for count in identity_counts.values() if count > 1
        )
        if rows_by_date:
            first_day = date.fromisoformat(min(rows_by_date))
            last_day = date.fromisoformat(max(rows_by_date))
            span_days = (last_day - first_day).days + 1
            missing_days = {
                (first_day + timedelta(days=offset)).isoformat()
                for offset in range(span_days)
                if (first_day + timedelta(days=offset)).isoformat() not in rows_by_date
            }
        else:
            first_day = last_day = None
            span_days = 0
            missing_days = set()

        expected_rank_count = 200
        daily_records: list[dict[str, Any]] = []
        year_records: list[dict[str, Any]] = []
        month_records: list[dict[str, Any]] = []
        years = range(start_year, end_year + 1)
        for year in years:
            year_start = date(year, 1, 1)
            year_end = date(year + 1, 1, 1)
            observed_year = {
                day: count
                for day, count in rows_by_date.items()
                if day.startswith(f"{year:04d}-")
            }
            calendar_days = (year_end - year_start).days
            incomplete_dates = sum(
                1 for count in observed_year.values() if count != expected_rank_count
            )
            year_records.append(
                {
                    "year": year,
                    "calendar_days": calendar_days,
                    "observed_dates": len(observed_year),
                    "calendar_missing_dates": calendar_days - len(observed_year),
                    "observations": sum(observed_year.values()),
                    "incomplete_observed_dates": incomplete_dates,
                    "first_observed_date": min(observed_year) if observed_year else "",
                    "last_observed_date": max(observed_year) if observed_year else "",
                    "coverage_interpretation": (
                        "Calendar-day diagnostic only; expected publication schedule is unverified."
                    ),
                }
            )
            for month in range(1, 13):
                month_start = date(year, month, 1)
                month_end = date(year + (1 if month == 12 else 0), month % 12 + 1, 1)
                month_days = (month_end - month_start).days
                observed_month = {
                    day: count
                    for day, count in observed_year.items()
                    if day[5:7] == f"{month:02d}"
                }
                month_records.append(
                    {
                        "month": f"{year:04d}-{month:02d}",
                        "calendar_days": month_days,
                        "observed_dates": len(observed_month),
                        "calendar_missing_dates": month_days - len(observed_month),
                        "observations": sum(observed_month.values()),
                        "incomplete_observed_dates": sum(
                            1 for count in observed_month.values()
                            if count != expected_rank_count
                        ),
                        "coverage_interpretation": (
                            "Calendar-day diagnostic only; expected publication schedule is unverified."
                        ),
                    }
                )

        if first_day is not None and last_day is not None:
            current = first_day
            while current <= last_day:
                count = rows_by_date.get(current.isoformat(), 0)
                daily_records.append(
                    {
                        "chart_date": current.isoformat(),
                        "observed_rows": count,
                        "expected_top200_rows": expected_rank_count,
                        "status": (
                            "GAP_CANDIDATE"
                            if count == 0
                            else "OBSERVED_INCOMPLETE_ROW_COUNT"
                            if count != expected_rank_count
                            else "OBSERVED"
                        ),
                        "coverage_interpretation": (
                            "Calendar-step gap candidate only; source reporting schedule is unverified."
                        ),
                    }
                )
                current += timedelta(days=1)

        _write_csv(
            report_dir / "zenodo_mgdplus_us_chart_by_date.csv",
            ("chart_date", "observed_rows", "expected_top200_rows", "status", "coverage_interpretation"),
            daily_records,
        )
        _write_csv(
            report_dir / "zenodo_mgdplus_us_chart_by_year.csv",
            (
                "year", "calendar_days", "observed_dates", "calendar_missing_dates",
                "observations", "incomplete_observed_dates", "first_observed_date",
                "last_observed_date", "coverage_interpretation",
            ),
            year_records,
        )
        _write_csv(
            report_dir / "zenodo_mgdplus_us_chart_by_month.csv",
            (
                "month", "calendar_days", "observed_dates", "calendar_missing_dates",
                "observations", "incomplete_observed_dates", "coverage_interpretation",
            ),
            month_records,
        )

    rank_counts = Counter()
    for row in rank_values:
        rank_counts[row] += 1
    duplicate_stream_conflicts = sum(
        1
        for stream_values in streams_by_date_chart_position.values()
        if len(stream_values) > 1
    )
    has_viral_file = any(
        item.filename.startswith("charts/")
        and "viral" in item.filename.casefold()
        for item in members
    )
    total_uncompressed = sum(item.file_size for item in members)
    total_compressed = sum(item.compress_size for item in members)
    summary: dict[str, Any] = {
        "generated_at": datetime.now().astimezone().isoformat(),
        "archive": str(archive_path),
        "archive_bytes": archive_path.stat().st_size,
        "archive_sha256": sha256_file(archive_path),
        "archive_crc_test": "passed",
        "archive_member_count": len(members),
        "archive_total_uncompressed_member_bytes": total_uncompressed,
        "archive_total_compressed_member_bytes": total_compressed,
        "unsafe_member_path_count": sum(
            1 for item in member_records if item["is_unsafe_path"]
        ),
        "csv_member_count": sum(
            1 for item in members if item.filename.casefold().endswith(".csv")
        ),
        "ipynb_checkpoint_member_count": sum(
            1 for item in members if ".ipynb_checkpoints/" in item.filename.casefold()
        ),
        "regional_chart_country_file_count": len(region_codes),
        "regional_chart_country_codes": region_codes,
        "us_chart": {
            "member": US_CHART_MEMBER,
            "delimiter": "TAB",
            "headers": headers,
            "rows": row_count,
            "market_values": dict(market_counts),
            "chart_values": dict(chart_counts),
            "first_date": first_day.isoformat() if first_day else None,
            "last_date": last_day.isoformat() if last_day else None,
            "distinct_dates": len(rows_by_date),
            "calendar_days_in_observed_span": span_days,
            "calendar_gap_candidates_within_observed_span": len(missing_days),
            "missing_stream_rows": stream_missing,
            "invalid_stream_rows": stream_invalid,
            "missing_or_invalid_date_rows": date_invalid,
            "missing_track_id_rows": id_missing,
            "distinct_track_ids": len(unique_ids),
            "track_id_length_counts": dict(id_lengths),
            "rank_min": min(rank_values) if rank_values else None,
            "rank_max": max(rank_values) if rank_values else None,
            "rank_value_counts": dict(sorted(rank_counts.items())),
            "invalid_rank_rows": rank_invalid,
            "expected_top200_rank_count": expected_rank_count,
            "observed_dates_with_non_200_rows": sum(
                1 for count in rows_by_date.values() if count != expected_rank_count
            ),
            "duplicate_identity_groups": duplicate_groups,
            "duplicate_extra_rows": duplicate_extra_rows,
            "duplicate_identity_groups_with_stream_conflicts": duplicate_stream_conflicts,
            "daily_calendar_assumption": (
                "Gap dates are unverified candidates; no expected publication schedule was supplied."
            ),
        },
        "metadata_members": {
            "us_song_metadata_member_count": len(song_metadata_members),
            "us_song_metadata_members": song_metadata_members,
            "us_artist_metadata_member_count": len(artist_metadata_members),
            "us_artist_metadata_members": artist_metadata_members,
            "us_metadata_headers": metadata_schemas,
            "album_related_fields_found": sorted(
                {
                    header
                    for fields in metadata_schemas.values()
                    for header in fields
                    if "album" in header.casefold()
                }
            ),
            "artist_id_fields_found": sorted(
                {
                    header
                    for fields in metadata_schemas.values()
                    for header in fields
                    if "artist" in header.casefold() and "id" in header.casefold()
                }
            ),
        },
        "viral_chart_file_present": has_viral_file,
        "extraction_performed": False,
        "production_import_performed": False,
        "rights_status": "UNVERIFIED",
        "rights_note": (
            "Zenodo record CC BY 4.0 metadata does not establish rights to upstream Spotify-derived content, "
            "commercial analytics, or redistribution."
        ),
    }
    if compact_database is not None:
        if not compact_database.is_file():
            raise FileNotFoundError(compact_database)
        summary["cross_source_comparison"] = _cross_source_comparison(
            compact_database,
            dataset_id,
            dataset_version,
            streams_by_date_chart_position,
        )
    (report_dir / "zenodo_mgdplus_audit.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=True), encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "CRC-check and research-audit MGD+ ZIP contents without extracting or importing them."
        )
    )
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--report-dir", type=Path, required=True)
    parser.add_argument("--compact-db", type=Path)
    parser.add_argument("--dataset-id", default=DATASETS[1].dataset_id)
    parser.add_argument("--dataset-version", type=int, default=DATASETS[1].version)
    parser.add_argument("--start-year", type=int, default=2017)
    parser.add_argument("--end-year", type=int, default=2026)
    args = parser.parse_args()
    print(
        json.dumps(
            audit_archive(
                args.archive,
                args.report_dir,
                compact_database=args.compact_db,
                dataset_id=args.dataset_id,
                dataset_version=args.dataset_version,
                start_year=args.start_year,
                end_year=args.end_year,
            ),
            indent=2,
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
