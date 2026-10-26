from __future__ import annotations

import csv
from pathlib import Path

import pytest

from spotify_historical_analytics.db import DatabaseManager
from spotify_historical_analytics.import_sessions import (
    ImportSessionStore,
)


HEADERS = [
    "Date",
    "Track Name",
    "Artist",
    "Streams",
    "URL",
    "Region",
    "Position",
    "Chart",
    "Track ID",
    "Artist ID",
    "Album ID",
    "Album Name",
    "Mapped Artist Name",
]


def write_csv(path: Path, rows: list[list[object]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(HEADERS)
        writer.writerows(rows)


def make_row(
    date: str,
    name: str,
    artist: str,
    streams: object,
    region: str = "US",
    position: int = 1,
    chart: str = "daily",
    track_id: str = "track-one",
) -> list[object]:
    return [
        date,
        name,
        artist,
        streams,
        f"https://open.spotify.com/track/{track_id}",
        region,
        position,
        chart,
        track_id,
        "artist-one",
        "album-one",
        "Album One",
        "",
    ]


def test_chunked_staging_reports_validation_duplicates_and_conflicts(
    tmp_path: Path,
) -> None:
    source = tmp_path / "candidate.csv"
    write_csv(
        source,
        [
            make_row("2024-01-01", "Song", "Artist", 1000),
            make_row("2024-01-01", "Song", "Artist", 1000),
            make_row("2024-01-01", "Song", "Artist", 1100, position=2),
            make_row("2024-01-02", "Canada Song", "Artist", 2000, region="CA"),
            make_row("bad-date", "Broken", "Artist", 500),
        ],
    )
    store = ImportSessionStore(tmp_path / "staging.sqlite3")
    session_id = store.create_session(
        source, "Synthetic candidate", "Synthetic only", "daily"
    )

    summary = store.prepare(session_id)

    assert summary.status == "staged"
    assert summary.processed_rows == 5
    assert summary.accepted_rows == 3
    assert summary.rejected_rows == 2
    assert summary.exact_duplicates == 1
    assert summary.conflicts == 1
    assert summary.country_counts == {"US": 3}
    assert summary.rejection_counts == {
        "invalid_date": 1,
        "non_us_country:CA": 1,
    }
    assert summary.first_date == summary.last_date == "2024-01-01"
    assert len(store.rejection_samples(session_id)) == 2
    store.close()


def test_session_persists_and_changed_source_cannot_resume(tmp_path: Path) -> None:
    source = tmp_path / "candidate.csv"
    write_csv(source, [make_row("2024-01-01", "Song", "Artist", 1000)])
    store_path = tmp_path / "staging.sqlite3"
    store = ImportSessionStore(store_path)
    session_id = store.create_session(source, "Source", "Synthetic", "daily")
    store.prepare(session_id)
    store.close()

    resumed = ImportSessionStore(store_path)
    assert resumed.get_session(session_id)["status"] == "staged"
    with source.open("a", encoding="utf-8") as stream:
        stream.write("2024-01-02,New Song,Artist,2000,,US,2,daily,new-track\n")

    with pytest.raises(ValueError, match="source file changed"):
        resumed.prepare(session_id)
    assert resumed.get_session(session_id)["status"] == "stale"
    resumed.close()


def test_old_adapter_sessions_must_not_resume_under_new_mapping_rules(
    tmp_path: Path,
) -> None:
    source = tmp_path / "candidate.csv"
    write_csv(source, [make_row("2024-01-01", "Song", "Artist", 1000)])
    store = ImportSessionStore(tmp_path / "staging.sqlite3")
    session_id = store.create_session(source, "Source", "Synthetic", "daily")
    store.connection.execute(
        "UPDATE import_sessions SET adapter_version=1 WHERE session_id=?",
        (session_id,),
    )
    store.connection.commit()

    with pytest.raises(ValueError, match="adapter version"):
        store.prepare(session_id)
    store.close()


def test_staging_schema_v1_migrates_artist_name_column(tmp_path: Path) -> None:
    staging_path = tmp_path / "staging.sqlite3"
    store = ImportSessionStore(staging_path)
    store.connection.execute(
        "ALTER TABLE staged_chart_rows DROP COLUMN artist_name"
    )
    store.connection.execute("PRAGMA user_version=1")
    store.connection.commit()
    store.close()

    migrated = ImportSessionStore(staging_path)
    columns = {
        row["name"]
        for row in migrated.connection.execute("PRAGMA table_info(staged_chart_rows)")
    }
    assert "artist_name" in columns
    assert migrated.connection.execute("PRAGMA user_version").fetchone()[0] == 2
    migrated.close()


def test_local_import_without_manifest_is_transactional_and_idempotent(
    tmp_path: Path,
) -> None:
    source = tmp_path / "approved-synthetic.csv"
    write_csv(source, [make_row("2024-01-01", "Song", "Artist", 1000)])
    production = DatabaseManager(tmp_path / "production" / "analytics.db")
    staging_path = tmp_path / "staging.sqlite3"
    store = ImportSessionStore(staging_path)
    session_id = store.create_session(source, "Approved synthetic", "Test", "daily")
    store.prepare(session_id)

    result = store.finalize(session_id, production)
    assert result["imported_rows"] == 1
    assert result["duplicates_skipped"] == 0
    assert production.connection.execute(
        "SELECT COUNT(*) FROM chart_records"
    ).fetchone()[0] == 1
    assert production.connection.execute(
        "SELECT album_name FROM albums WHERE album_id='album-one'"
    ).fetchone()[0] == "Album One"
    assert production.connection.execute(
        "SELECT COUNT(*) FROM track_albums WHERE mapping_status='id_match'"
    ).fetchone()[0] == 1
    assert production.connection.execute(
        "SELECT COUNT(*) FROM track_artists"
    ).fetchone()[0] == 0
    assert production.connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    store.close()

    repeated = ImportSessionStore(staging_path)
    second_id = repeated.create_session(
        source, "Approved synthetic", "Test", "daily"
    )
    repeated.prepare(second_id)
    repeated_result = repeated.finalize(second_id, production)
    assert repeated_result["imported_rows"] == 0
    assert repeated_result["duplicates_skipped"] == 1
    assert production.connection.execute(
        "SELECT COUNT(*) FROM chart_records"
    ).fetchone()[0] == 1
    repeated.close()
    production.close()


def test_unvalidated_and_changed_sources_cannot_import(tmp_path: Path) -> None:
    source = tmp_path / "candidate.csv"
    write_csv(source, [make_row("2024-01-01", "Song", "Artist", 1000)])
    store = ImportSessionStore(tmp_path / "staging.sqlite3")
    production = DatabaseManager(tmp_path / "production.db")
    session_id = store.create_session(source, "Source", "Test", "daily")
    with pytest.raises(ValueError, match="Validate"):
        store.finalize(session_id, production)
    store.prepare(session_id)
    source.write_text(source.read_text(encoding="utf-8-sig") + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="changed"):
        store.finalize(session_id, production)
    assert production.connection.execute("SELECT COUNT(*) FROM chart_records").fetchone()[0] == 0
    production.close()
    store.close()


def test_duplicate_chart_rows_preserve_multiple_supplied_artist_ids(
    tmp_path: Path,
) -> None:
    source = tmp_path / "multi-credit.csv"
    first = make_row("2024-01-01", "Collaboration", "Artist One, Artist Two", 1000)
    second = list(first)
    second[9] = "artist-two"
    first[12] = "Artist One"
    second[12] = "Artist Two"
    write_csv(source, [first, second])
    production = DatabaseManager(tmp_path / "analytics.db")
    store = ImportSessionStore(tmp_path / "staging.sqlite3")
    session_id = store.create_session(source, "Synthetic credits", "Test", "daily")
    summary = store.prepare(session_id)
    assert summary.accepted_rows == 2
    assert summary.exact_duplicates == 1
    assert summary.artist_mapping_rows == 2

    result = store.finalize(session_id, production)

    assert result["imported_rows"] == 1
    assert result["duplicates_skipped"] == 1
    assert production.connection.execute(
        "SELECT COUNT(*) FROM chart_records"
    ).fetchone()[0] == 1
    assert production.connection.execute(
        "SELECT COUNT(*) FROM track_artists WHERE mapping_status='id_match'"
    ).fetchone()[0] == 2
    assert {
        tuple(row)
        for row in production.connection.execute(
            "SELECT artist_id, artist_name FROM artists ORDER BY artist_id"
        )
    } == {
        ("artist-one", "Artist One"),
        ("artist-two", "Artist Two"),
    }
    assert production.get_summary(chart_type="daily")["total_streams"] == 1000
    store.close()
    production.close()


def test_conflict_with_existing_source_rolls_back_batch_and_preserves_audit(
    tmp_path: Path,
) -> None:
    production = DatabaseManager(tmp_path / "analytics.db")
    staging_path = tmp_path / "staging.sqlite3"
    store = ImportSessionStore(staging_path)
    first_file = tmp_path / "first.csv"
    write_csv(first_file, [make_row("2024-01-01", "Song", "Artist", 1000)])
    first_id = store.create_session(first_file, "Same source", "Test", "daily")
    store.prepare(first_id)
    store.finalize(first_id, production)

    conflicting_file = tmp_path / "conflicting.csv"
    write_csv(
        conflicting_file, [make_row("2024-01-01", "Song", "Artist", 1100)]
    )
    second_id = store.create_session(
        conflicting_file, "Same source", "Test", "daily"
    )
    store.prepare(second_id)
    before_batches = production.connection.execute(
        "SELECT COUNT(*) FROM import_batches"
    ).fetchone()[0]

    with pytest.raises(ValueError, match="conflicts with an existing production"):
        store.finalize(second_id, production)

    assert production.connection.execute(
        "SELECT COUNT(*) FROM chart_records"
    ).fetchone()[0] == 1
    assert production.connection.execute(
        "SELECT COUNT(*) FROM import_batches"
    ).fetchone()[0] == before_batches
    assert production.connection.execute(
        "SELECT COUNT(*) FROM import_rights_approvals"
    ).fetchone()[0] == 0
    assert production.connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    store.close()
    production.close()


def test_cancel_at_checkpoint_preserves_reusable_session(tmp_path: Path) -> None:
    source = tmp_path / "candidate.csv"
    write_csv(
        source,
        [make_row(f"2024-01-{day:02}", f"Song {day}", "Artist", 1000) for day in range(1, 4)],
    )
    store = ImportSessionStore(tmp_path / "staging.sqlite3")
    session_id = store.create_session(source, "Source", "Test", "daily")

    class CancelImmediately:
        @staticmethod
        def is_set() -> bool:
            return True

    summary = store.prepare(session_id, cancel_event=CancelImmediately())
    assert summary.status == "paused"
    assert summary.accepted_rows == 0
    resumed = store.prepare(session_id)
    assert resumed.status == "staged"
    assert resumed.accepted_rows == 3
    store.close()


def test_weekly_rows_require_explicit_boundaries_and_missing_schema_fails(
    tmp_path: Path,
) -> None:
    source = tmp_path / "weekly.csv"
    write_csv(source, [make_row("2024-01-01", "Song", "Artist", 1000, chart="weekly")])
    store = ImportSessionStore(tmp_path / "staging.sqlite3")
    session_id = store.create_session(source, "Weekly source", "Test", "weekly")
    summary = store.prepare(session_id)
    assert summary.accepted_rows == 0
    assert summary.rejection_counts == {"missing_week_boundaries": 1}

    invalid = tmp_path / "missing-region.csv"
    invalid.write_text(
        "Date,Track,Artist,Streams\n2024-01-01,Song,Artist,1000\n",
        encoding="utf-8",
    )
    invalid_id = store.create_session(invalid, "Missing region", "Test", "daily")
    with pytest.raises(ValueError, match="region/country"):
        store.prepare(invalid_id)
    store.close()


def test_cancellation_during_transaction_rolls_back_rows_and_metadata(tmp_path, monkeypatch):
    import threading

    source = tmp_path / "cancel.csv"
    write_csv(source, [make_row(f"2024-01-{day:02d}", f"Song {day}", "Artist", 100,
                               track_id=f"track-{day}") for day in range(1, 4)])
    store = ImportSessionStore(tmp_path / "staging.db")
    session = store.create_session(source, "Cancellation fixture", "Test only", "daily")
    store.prepare(session)
    database = DatabaseManager(tmp_path / "production.db")
    cancel = threading.Event()
    monkeypatch.setattr("spotify_historical_analytics.import_sessions.CHUNK_SIZE", 1)
    with pytest.raises(InterruptedError, match="cancelled"):
        store.finalize(session, database, lambda *_: cancel.set(), cancel)
    for table in ("chart_records", "import_batches", "albums", "track_albums", "sources"):
        assert database.connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
    assert database.connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
    assert store.get_session(session)["status"] == "staged"
    database.close()
    store.close()
