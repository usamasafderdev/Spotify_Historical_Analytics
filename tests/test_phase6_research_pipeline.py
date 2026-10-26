from __future__ import annotations

import argparse
import csv
import json
import os
import sqlite3
import time
from collections.abc import Iterator
from pathlib import Path

import pytest

from scripts.download_historical_datasets import (
    _lock_file,
    _lock_owner_is_running,
    _release_lock,
    _active_archive_paths,
    _existing_cache,
    download_dataset,
)
from scripts import download_historical_datasets as downloader
from spotify_historical_analytics.db import DatabaseManager
from spotify_historical_analytics.research_pipeline import (
    DATASETS,
    _initialize_staging,
    approve_source_rights,
    classify_category,
    detect_columns,
    inventory_file,
    normalize_region,
    process_file,
    production_import_records,
    write_analysis_reports,
)


def _write_song_file(path: Path, rows: list[list[str]]) -> Path:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(
            ["date", "region", "chart", "rank", "track_id", "title", "artist", "streams"]
        )
        writer.writerows(rows)
    return path


@pytest.fixture
def staging_db(tmp_path: Path) -> Iterator[sqlite3.Connection]:
    connection = sqlite3.connect(tmp_path / "research.sqlite")
    _initialize_staging(connection)
    yield connection
    connection.close()


def test_inventory_counts_jsonl_rows_without_loading_the_file(tmp_path: Path) -> None:
    source = tmp_path / "charts_songs_daily.jsonl"
    source.write_text(
        '{"date":"2017-01-01","region":"US","rank":1}\n'
        '{"date":"2017-01-02","region":"US","rank":2}\n',
        encoding="utf-8",
    )

    record = inventory_file(
        source,
        DATASETS[0].dataset_id,
        DATASETS[0].version,
        DATASETS[0].url,
        DATASETS[0].listed_license,
    )

    assert record["row_count"] == 2
    assert json.loads(record["column_names_json"]) == ["date", "region", "rank"]


def test_region_normalization_only_accepts_verified_us_names() -> None:
    assert normalize_region("US") == "US"
    assert normalize_region("USA") == "US"
    assert normalize_region("United States") == "US"
    assert normalize_region("United States of America") == "US"
    assert normalize_region("U") is None
    assert normalize_region("Global") is None
    assert normalize_region("Canada") is None
    assert normalize_region(None) is None


def test_schema_detection_and_category_classification_are_source_aware() -> None:
    columns = detect_columns(
        ["chart_date", "country", "position", "track_name", "track_id", "streams"]
    )
    assert columns == {
        "chart_date": "chart_date",
        "country": "country",
        "position": "position",
        "track_name": "track_name",
        "track_id": "track_id",
        "streams": "streams",
    }
    assert classify_category("charts_songs_daily.csv.gz", columns) == "songs"
    assert classify_category("charts_albums_weekly.csv.gz", {}) == "albums"
    assert classify_category("charts_artists_daily.csv.gz", {}) == "artists"


def test_csv_chunk_processing_filters_non_us_rejects_bad_fields_and_is_idempotent(
    tmp_path: Path, staging_db: sqlite3.Connection
) -> None:
    file_path = _write_song_file(
        tmp_path / "charts_songs_daily.csv",
        [
            ["2017-01-01", "US", "top200", "1", "track-a", "Song A", "Artist A", "0"],
            ["2017-01-02", "Global", "top200", "2", "track-b", "Song B", "Artist B", "10"],
            ["not-a-date", "USA", "top200", "3", "track-c", "Song C", "Artist C", "10"],
            ["2017-01-04", "United States", "top200", "4", "track-d", "Song D", "Artist D", "bad"],
            ["2017-01-05", "", "top200", "5", "track-e", "Song E", "Artist E", "20"],
        ],
    )
    result = process_file(staging_db, DATASETS[0], file_path, chunk_size=2)
    assert result == {
        "status": "complete",
        "rows_seen": 5,
        "rows_accepted": 1,
        "rows_rejected": 4,
    }
    assert staging_db.execute("SELECT streams FROM staged_observations").fetchone()[0] == 0
    reasons = {
        row[0]
        for row in staging_db.execute("SELECT reason FROM staged_rejections").fetchall()
    }
    assert "non_us_or_unknown_region" in reasons
    assert "invalid_or_missing_chart_date" in reasons
    assert "invalid_stream_count:not_numeric" in reasons

    again = process_file(staging_db, DATASETS[0], file_path, chunk_size=1)
    assert again["status"] == "reused"
    assert staging_db.execute("SELECT COUNT(*) FROM staged_observations").fetchone()[0] == 1
    assert staging_db.execute("SELECT COUNT(*) FROM staged_rejections").fetchone()[0] == 4


def test_track_ids_are_extracted_only_from_verified_spotify_track_urls(
    tmp_path: Path,
    staging_db: sqlite3.Connection,
) -> None:
    source = tmp_path / "charts_songs_daily.csv"
    source.write_text(
        "date,region,chart,rank,title,artist,url,streams\n"
        "2017-01-01,US,top200,1,Song A,Artist A,"
        "https://open.spotify.com/track/4Km5HrUvYTaSUfiSGPJeQR?si=example,100\n"
        "2017-01-01,US,top200,2,Song B,Artist B,"
        "https://example.com/track/4Km5HrUvYTaSUfiSGPJeQR,90\n",
        encoding="utf-8",
    )

    process_file(staging_db, DATASETS[0], source)

    assert staging_db.execute(
        "SELECT track_id FROM staged_observations ORDER BY position"
    ).fetchall() == [("4Km5HrUvYTaSUfiSGPJeQR",), (None,)]
    staging_db.execute(
        "UPDATE staged_files SET processing_version=1"
    )
    staging_db.execute(
        "UPDATE staged_observations SET track_id=NULL WHERE position=1"
    )
    staging_db.commit()

    result = process_file(staging_db, DATASETS[0], source)

    assert result["status"] == "complete"
    assert staging_db.execute(
        "SELECT track_id FROM staged_observations WHERE position=1"
    ).fetchone()[0] == "4Km5HrUvYTaSUfiSGPJeQR"


def test_null_streams_are_not_reinterpreted_as_zero(tmp_path: Path, staging_db: sqlite3.Connection) -> None:
    file_path = _write_song_file(
        tmp_path / "charts_songs_daily.csv",
        [["2017-01-01", "US", "viral50", "1", "track-a", "Song A", "Artist A", "NULL"]],
    )
    result = process_file(staging_db, DATASETS[0], file_path)
    assert result["rows_accepted"] == 1
    assert staging_db.execute("SELECT streams FROM staged_observations").fetchone()[0] is None


def test_downloader_reuses_pinned_local_cache_without_network(tmp_path: Path) -> None:
    spec = DATASETS[0]
    cached = (
        tmp_path / spec.research_folder / "datasets" / spec.owner / spec.slug
        / "versions" / str(spec.version)
    )
    cached.mkdir(parents=True)
    (cached / "source.csv").write_text("date,region\n", encoding="utf-8")
    result = download_dataset(spec, tmp_path)
    assert result["status"] == "REUSED"
    assert Path(result["path"]) == cached
    assert list((tmp_path / ".locks").glob("*.lock")) == []


def test_downloader_detects_kagglehub_archive_path_and_avoids_partial_cache(
    tmp_path: Path,
) -> None:
    spec = DATASETS[0]
    versions = tmp_path / "datasets" / spec.owner / spec.slug / "versions"
    candidate = versions / str(spec.version)
    candidate.mkdir(parents=True)
    (candidate / "partial.csv").write_text("incomplete", encoding="utf-8")
    archive = versions / f"{spec.version}.archive"
    archive.write_bytes(b"partial archive")

    assert _active_archive_paths(tmp_path, spec) == [archive]
    assert _existing_cache(tmp_path, spec) is None


def test_downloader_skips_partial_files_without_deleting_or_reading_them(
    tmp_path: Path,
) -> None:
    spec = DATASETS[0]
    root = tmp_path / spec.research_folder
    root.mkdir()
    partial = root / "download.csv.partial"
    partial.write_bytes(b"still-being-written")
    result = download_dataset(spec, tmp_path)
    assert result["status"] == "SKIPPED_ACTIVE_OR_PARTIAL_DOWNLOAD"
    assert partial.read_bytes() == b"still-being-written"


def test_downloader_lock_records_owner_and_is_released(tmp_path: Path) -> None:
    lock_path = tmp_path / "dataset.lock"
    descriptor = _lock_file(lock_path)
    assert descriptor is not None
    try:
        owner = json.loads(lock_path.read_text(encoding="utf-8"))
        assert owner["pid"] > 0
        assert owner["created_at"] > 0
        assert _lock_owner_is_running(lock_path)
    finally:
        _release_lock(lock_path, descriptor)
    assert not lock_path.exists()


def test_downloader_recovers_expired_malformed_lock(tmp_path: Path) -> None:
    lock_path = tmp_path / "stale.lock"
    lock_path.write_text("{", encoding="utf-8")
    expired_at = time.time() - 7 * 60 * 60
    os.utime(lock_path, (expired_at, expired_at))

    descriptor = _lock_file(lock_path)
    assert descriptor is not None
    try:
        assert json.loads(lock_path.read_text(encoding="utf-8"))["pid"] > 0
    finally:
        _release_lock(lock_path, descriptor)


def test_audit_only_preserves_the_original_download_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    status_path = tmp_path / "reports" / "dataset_download_status.json"
    status_path.parent.mkdir(parents=True)
    original = {"download_attempted": True, "datasets": [{"status": "REUSED"}]}
    status_path.write_text(json.dumps(original), encoding="utf-8")
    monkeypatch.setattr(
        downloader,
        "parse_args",
        lambda: argparse.Namespace(
            chunk_size=10,
            research_root=tmp_path,
            download=False,
            audit_only=True,
        ),
    )
    monkeypatch.setattr(downloader, "run_audit", lambda *_: None)

    assert downloader.main() == 0
    assert json.loads(status_path.read_text(encoding="utf-8")) == original


def test_downloader_records_errors_without_exposing_kaggle_tokens(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import kagglehub

    def fail_download(*_args: object, **_kwargs: object) -> str:
        assert _args and _kwargs
        raise RuntimeError("KAGGLE_API_TOKEN=secret-value")

    monkeypatch.setattr(kagglehub, "dataset_download", fail_download)
    monkeypatch.setenv("KAGGLEHUB_CACHE", str(tmp_path / "cache"))
    result = download_dataset(DATASETS[0], tmp_path)
    assert result["status"] == "DOWNLOAD_FAILED"
    assert "secret-value" not in result["details"]
    assert "[REDACTED]" in result["details"]


def test_missing_region_is_not_assumed_to_be_us(tmp_path: Path, staging_db: sqlite3.Connection) -> None:
    file_path = _write_song_file(
        tmp_path / "songs.csv",
        [["2017-01-01", "", "top200", "1", "track-a", "Song A", "Artist A", "1"]],
    )
    result = process_file(staging_db, DATASETS[0], file_path)
    assert result["rows_accepted"] == 0
    assert staging_db.execute(
        "SELECT reason FROM staged_rejections"
    ).fetchone()[0] == "non_us_or_unknown_region"


def test_report_detects_cross_source_conflicts_without_summing(
    tmp_path: Path, staging_db: sqlite3.Connection
) -> None:
    source_one = _write_song_file(
        tmp_path / "charts_songs_daily.csv",
        [["2017-01-01", "US", "top200", "1", "same-track", "Song A", "Artist A", "100"]],
    )
    source_two = _write_song_file(
        tmp_path / "other_songs_daily.csv",
        [["2017-01-01", "USA", "top200", "1", "same-track", "Song A", "Artist A", "101"]],
    )
    process_file(staging_db, DATASETS[0], source_one)
    process_file(staging_db, DATASETS[1], source_two)
    counts = write_analysis_reports(staging_db, tmp_path / "reports")
    assert counts["data_conflicts"] == 1
    assert counts["source_overlap"] == 0
    assert staging_db.execute("SELECT COUNT(*) FROM staged_observations").fetchone()[0] == 2
    report_rows = list(
        csv.DictReader((tmp_path / "reports" / "data_conflicts.csv").open(encoding="utf-8-sig"))
    )
    assert report_rows[0]["streams_json"] == "[100, 101]"
    assert report_rows[0]["status"] == "CONFLICTING_OBSERVATION"
    summary = (tmp_path / "reports" / "deduplication_summary.md").read_text(encoding="utf-8")
    assert "No records were summed, deleted" in summary


def test_identical_cross_source_records_are_reported_as_duplicates(
    tmp_path: Path, staging_db: sqlite3.Connection
) -> None:
    one = _write_song_file(
        tmp_path / "charts_songs_daily.csv",
        [["2017-01-01", "US", "top200", "1", "same-track", "Song A", "Artist A", "100"]],
    )
    two = _write_song_file(
        tmp_path / "other_songs_daily.csv",
        [["2017-01-01", "USA", "top200", "1", "same-track", "Song A", "Artist A", "100"]],
    )
    process_file(staging_db, DATASETS[0], one)
    process_file(staging_db, DATASETS[1], two)
    counts = write_analysis_reports(staging_db, tmp_path / "reports")
    assert counts["source_overlap"] == 1
    assert counts["data_conflicts"] == 0


def test_title_only_matches_are_not_counted_as_duplicates(
    tmp_path: Path, staging_db: sqlite3.Connection
) -> None:
    one = _write_song_file(
        tmp_path / "charts_songs_daily.csv",
        [["2017-01-01", "US", "top200", "1", "", "Same title", "Artist", "100"]],
    )
    two = _write_song_file(
        tmp_path / "other_songs_daily.csv",
        [["2017-01-01", "US", "top200", "1", "", "Same title", "Artist", "100"]],
    )
    process_file(staging_db, DATASETS[0], one)
    process_file(staging_db, DATASETS[1], two)
    counts = write_analysis_reports(staging_db, tmp_path / "reports")
    assert counts["source_overlap"] == 0
    assert counts["data_conflicts"] == 0


def test_missing_dates_are_reported_as_unverified_gaps_not_zero_streams(
    tmp_path: Path, staging_db: sqlite3.Connection
) -> None:
    file_path = _write_song_file(
        tmp_path / "charts_songs_daily.csv",
        [
            ["2017-01-01", "US", "top200", "1", "track-a", "Song A", "Artist A", "0"],
            ["2017-01-03", "US", "top200", "1", "track-a", "Song A", "Artist A", "20"],
        ],
    )
    process_file(staging_db, DATASETS[0], file_path)
    write_analysis_reports(staging_db, tmp_path / "reports")
    with (tmp_path / "reports" / "missing_dates.csv").open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        gaps = list(csv.DictReader(stream))
    assert [row["candidate_missing_chart_date"] for row in gaps] == ["2017-01-02"]
    assert "not a zero-stream record" in gaps[0]["interpretation"]
    with (tmp_path / "reports" / "coverage_by_year.csv").open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        coverage = next(
            row for row in csv.DictReader(stream) if row["observation_count"] == "2"
        )
    assert coverage["observation_count"] == "2"
    assert coverage["rows_with_streams"] == "2"
    assert "not proof" in coverage["coverage_assumption"]


def test_empty_staging_reports_all_target_years_as_unverified(
    tmp_path: Path, staging_db: sqlite3.Connection
) -> None:
    write_analysis_reports(staging_db, tmp_path / "reports")
    with (tmp_path / "reports" / "coverage_by_year.csv").open(
        encoding="utf-8-sig", newline=""
    ) as stream:
        rows = list(csv.DictReader(stream))
    assert len(rows) == 40
    assert {row["period"] for row in rows} == {str(year) for year in range(2017, 2027)}
    assert all(row["observation_count"] == "0" for row in rows)
    assert all(row["coverage_status"] == "NO_VALIDATED_OBSERVATIONS" for row in rows)


def test_staging_schema_migration_preserves_rows_but_does_not_promote_old_approval(
    tmp_path: Path,
) -> None:
    connection = sqlite3.connect(tmp_path / "older-staging.sqlite")
    connection.executescript(
        """
        CREATE TABLE staged_files (
            dataset_id TEXT NOT NULL, dataset_version INTEGER NOT NULL,
            file_sha256 TEXT NOT NULL, file_path TEXT NOT NULL, status TEXT NOT NULL,
            rows_seen INTEGER NOT NULL DEFAULT 0, rows_accepted INTEGER NOT NULL DEFAULT 0,
            rows_rejected INTEGER NOT NULL DEFAULT 0, started_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            completed_at TEXT, error TEXT,
            PRIMARY KEY (dataset_id, dataset_version, file_sha256)
        );
        CREATE TABLE staged_observations (
            id INTEGER PRIMARY KEY, dataset_id TEXT NOT NULL, dataset_version INTEGER NOT NULL,
            file_sha256 TEXT NOT NULL, source_row INTEGER NOT NULL, category TEXT NOT NULL,
            cadence TEXT NOT NULL, chart_name TEXT, country TEXT NOT NULL,
            chart_date TEXT NOT NULL, position INTEGER NOT NULL, track_id TEXT,
            track_name TEXT, artist_id TEXT, artist_name TEXT, album_id TEXT,
            album_name TEXT, streams INTEGER,
            UNIQUE(dataset_id, dataset_version, file_sha256, source_row)
        );
        CREATE TABLE source_rights (
            dataset_id TEXT PRIMARY KEY, rights_status TEXT NOT NULL DEFAULT 'UNVERIFIED',
            evidence_path TEXT, reviewed_by TEXT, reviewed_at TEXT, notes TEXT
        );
        INSERT INTO staged_observations(
            dataset_id, dataset_version, file_sha256, source_row, category, cadence,
            country, chart_date, position, track_id, track_name, streams
        ) VALUES ('example/source', 85, 'hash', 1, 'songs', 'daily', 'US',
                  '2017-01-01', 1, 'track-1', 'Song', 42);
        INSERT INTO staged_files(
            dataset_id, dataset_version, file_sha256, file_path, status, rows_seen
        ) VALUES ('example/source', 85, 'hash', 'source.csv', 'complete', 1);
        INSERT INTO source_rights(dataset_id, rights_status) VALUES ('example/source', 'APPROVED');
        """
    )
    _initialize_staging(connection)
    migrated = connection.execute(
        "SELECT chart_date, streams, raw_json FROM staged_observations"
    ).fetchone()
    assert tuple(migrated) == ("2017-01-01", 42, "{}")
    old_right = connection.execute(
        "SELECT rights_status FROM source_rights WHERE dataset_id=? AND dataset_version=0",
        ("example/source",),
    ).fetchone()
    assert old_right[0] == "APPROVED"
    assert connection.execute(
        "SELECT processing_version FROM staged_files WHERE file_sha256='hash'"
    ).fetchone()[0] == 1
    assert connection.execute(
        "SELECT 1 FROM source_rights WHERE dataset_id=? AND dataset_version=85",
        ("example/source",),
    ).fetchone() is None
    assert connection.execute("PRAGMA user_version").fetchone()[0] == 3
    connection.close()


def test_permission_gate_prevents_production_import_until_evidence_is_recorded(
    tmp_path: Path, staging_db: sqlite3.Connection
) -> None:
    file_path = _write_song_file(
        tmp_path / "charts_songs_daily.csv",
        [["2017-01-01", "US", "top200", "1", "track-a", "Song A", "Artist A", "100"]],
    )
    process_file(staging_db, DATASETS[0], file_path)
    app_db = DatabaseManager(tmp_path / "production.db")
    with pytest.raises(PermissionError, match="rights approval"):
        production_import_records(staging_db, app_db, DATASETS[0].dataset_id, DATASETS[0].version)
    assert app_db.connection.execute("SELECT COUNT(*) FROM chart_records").fetchone()[0] == 0
    app_db.close()


def test_approved_import_is_explicit_and_keeps_daily_stream_totals(
    tmp_path: Path, staging_db: sqlite3.Connection
) -> None:
    file_path = _write_song_file(
        tmp_path / "charts_songs_daily.csv",
        [
            ["2017-01-01", "US", "top200", "1", "track-a", "Song A", "Artist A", "100"],
            ["2017-01-02", "US", "top200", "1", "track-a", "Song A", "Artist A", "200"],
        ],
    )
    process_file(staging_db, DATASETS[0], file_path, chunk_size=1)
    evidence = tmp_path / "permission-review.txt"
    evidence.write_text("External written permission reference for test only.", encoding="utf-8")
    approval = tmp_path / "approval.json"
    approval.write_text(
        json.dumps(
            {
                "dataset_id": DATASETS[0].dataset_id,
                "dataset_version": DATASETS[0].version,
                "reviewed_by": "Test Reviewer",
                "reviewed_at": "2026-10-26",
                "evidence_path": evidence.name,
            }
        ),
        encoding="utf-8",
    )
    approve_source_rights(staging_db, approval)

    app_db = DatabaseManager(tmp_path / "production.db")
    inserted = production_import_records(
        staging_db, app_db, DATASETS[0].dataset_id, DATASETS[0].version
    )
    assert inserted == 2
    assert app_db.connection.execute("SELECT SUM(streams) FROM chart_records").fetchone()[0] == 300
    assert app_db.connection.execute(
        "SELECT DISTINCT chart_type FROM chart_records"
    ).fetchone()[0] == "daily"
    assert production_import_records(
        staging_db, app_db, DATASETS[0].dataset_id, DATASETS[0].version
    ) == 0
    assert app_db.connection.execute("SELECT COUNT(*) FROM chart_records").fetchone()[0] == 2
    app_db.close()


def test_album_rows_do_not_map_streams_from_popularity(
    tmp_path: Path, staging_db: sqlite3.Connection
) -> None:
    album_file = tmp_path / "charts_albums_weekly.csv"
    album_file.write_text(
        "date,region,rank,album_id,album_name,artist,popularity\n"
        "2020-01-01,US,1,album-a,Album A,Artist A,99\n",
        encoding="utf-8",
    )
    result = process_file(staging_db, DATASETS[0], album_file)
    assert result["rows_accepted"] == 1
    row = staging_db.execute(
        "SELECT category, cadence, streams, album_id FROM staged_observations"
    ).fetchone()
    assert tuple(row) == ("albums", "weekly", None, "album-a")
    # Even after a test-only explicit status update, album rows stay out of song totals.
    staging_db.execute(
        "UPDATE source_rights SET rights_status='APPROVED' WHERE dataset_id=? AND dataset_version=?",
        (DATASETS[0].dataset_id, DATASETS[0].version),
    )
    app_db = DatabaseManager(tmp_path / "production.db")
    try:
        assert production_import_records(
            staging_db, app_db, DATASETS[0].dataset_id, DATASETS[0].version
        ) == 0
        assert app_db.connection.execute("SELECT COUNT(*) FROM chart_records").fetchone()[0] == 0
    finally:
        app_db.close()


def test_production_import_rolls_back_all_database_writes_on_failure(
    tmp_path: Path, staging_db: sqlite3.Connection
) -> None:
    file_path = _write_song_file(
        tmp_path / "charts_songs_daily.csv",
        [["2017-01-01", "US", "top200", "1", "track-a", "Song A", "Artist A", "100"]],
    )
    process_file(staging_db, DATASETS[0], file_path)
    evidence = tmp_path / "permission-review.txt"
    evidence.write_text("reviewed", encoding="utf-8")
    approval = tmp_path / "approval.json"
    approval.write_text(
        json.dumps(
            {
                "dataset_id": DATASETS[0].dataset_id,
                "dataset_version": DATASETS[0].version,
                "reviewed_by": "Test Reviewer",
                "reviewed_at": "2026-10-26",
                "evidence_path": evidence.name,
            }
        ),
        encoding="utf-8",
    )
    approve_source_rights(staging_db, approval)
    app_db = DatabaseManager(tmp_path / "production.db")
    app_db.connection.execute(
        """
        CREATE TRIGGER abort_chart_insert BEFORE INSERT ON chart_records
        BEGIN SELECT RAISE(ABORT, 'fixture failure'); END
        """
    )
    app_db.connection.commit()
    with pytest.raises(sqlite3.IntegrityError, match="fixture failure"):
        production_import_records(
            staging_db, app_db, DATASETS[0].dataset_id, DATASETS[0].version
        )
    for table in ("sources", "import_batches", "chart_records"):
        assert app_db.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
    app_db.close()


def test_weekly_production_import_requires_explicit_period_boundaries(
    tmp_path: Path, staging_db: sqlite3.Connection
) -> None:
    daily_file = _write_song_file(
        tmp_path / "songs_daily.csv",
        [["2017-01-01", "US", "top200", "1", "daily-id", "Daily song", "Artist", "100"]],
    )
    weekly_file = tmp_path / "songs_weekly.csv"
    weekly_file.write_text(
        "date,region,chart,rank,track_id,title,artist,streams\n"
        "2017-01-08,US,top200,1,weekly-id,Weekly song,Artist,200\n",
        encoding="utf-8",
    )
    process_file(staging_db, DATASETS[0], daily_file)
    process_file(staging_db, DATASETS[0], weekly_file)
    evidence = tmp_path / "permission-review.txt"
    evidence.write_text("reviewed", encoding="utf-8")
    approval = tmp_path / "approval.json"
    approval.write_text(
        json.dumps(
            {
                "dataset_id": DATASETS[0].dataset_id,
                "dataset_version": DATASETS[0].version,
                "reviewed_by": "Test Reviewer",
                "reviewed_at": "2026-10-26",
                "evidence_path": evidence.name,
            }
        ),
        encoding="utf-8",
    )
    approve_source_rights(staging_db, approval)
    app_db = DatabaseManager(tmp_path / "production.db")
    with pytest.raises(ValueError, match="explicit week_start and week_end"):
        production_import_records(
            staging_db, app_db, DATASETS[0].dataset_id, DATASETS[0].version
        )
    assert app_db.connection.execute("SELECT COUNT(*) FROM chart_records").fetchone()[0] == 0
    assert app_db.connection.execute("SELECT COUNT(*) FROM import_batches").fetchone()[0] == 0
    app_db.close()


def test_weekly_import_keeps_explicit_dates_and_daily_rows_separate(
    tmp_path: Path, staging_db: sqlite3.Connection
) -> None:
    weekly_file = tmp_path / "songs_weekly.csv"
    weekly_file.write_text(
        "date,week_start,week_end,region,chart,rank,track_id,title,artist,streams\n"
        "2017-01-08,2017-01-02,2017-01-08,US,top200,1,weekly-id,Weekly song,Artist,200\n",
        encoding="utf-8",
    )
    process_file(staging_db, DATASETS[0], weekly_file)
    evidence = tmp_path / "permission-review.txt"
    evidence.write_text("reviewed", encoding="utf-8")
    approval = tmp_path / "approval.json"
    approval.write_text(
        json.dumps(
            {
                "dataset_id": DATASETS[0].dataset_id,
                "dataset_version": DATASETS[0].version,
                "reviewed_by": "Test Reviewer",
                "reviewed_at": "2026-10-26",
                "evidence_path": evidence.name,
            }
        ),
        encoding="utf-8",
    )
    approve_source_rights(staging_db, approval)
    app_db = DatabaseManager(tmp_path / "production.db")
    assert production_import_records(
        staging_db, app_db, DATASETS[0].dataset_id, DATASETS[0].version
    ) == 1
    row = app_db.connection.execute(
        "SELECT chart_type, weekly_start, weekly_end FROM chart_records"
    ).fetchone()
    assert tuple(row) == ("weekly", "2017-01-02", "2017-01-08")
    app_db.close()
