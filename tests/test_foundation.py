from __future__ import annotations

from pathlib import Path
import sqlite3

import pytest

from spotify_historical_analytics.db import DatabaseManager
from spotify_historical_analytics.importer import import_csv_file


FIXTURE_CSV = Path(__file__).parent / "fixtures" / "synthetic_us_daily.csv"


def test_csv_schema_mapping_and_us_filtering(tmp_path: Path) -> None:
    db = DatabaseManager(tmp_path / "analysis.db")
    result = import_csv_file(
        db=db,
        csv_path=FIXTURE_CSV,
        source_name="Test Source",
        source_license="Test license",
        chart_type="daily",
        country="US",
    )

    assert result.valid_rows == 5
    assert result.rejected_rows == 3
    assert result.duplicates_skipped == 1

    summary = db.get_summary(chart_type="daily")
    assert summary["total_streams"] == 49500
    assert summary["distinct_tracks"] == 2
    assert summary["distinct_artists"] == 2
    assert summary["chart_dates_with_data"] == 4
    database_path = db.db_path
    db.close()
    reopened = DatabaseManager(database_path)
    assert reopened.get_summary(chart_type="daily")["total_streams"] == 49500
    reopened.close()


def test_duplicate_imports_and_backup_restore(tmp_path: Path) -> None:
    db = DatabaseManager(tmp_path / "dup.db")
    first = import_csv_file(db, FIXTURE_CSV, "Test Source", "Test license", chart_type="daily", country="US")
    second = import_csv_file(db, FIXTURE_CSV, "Test Source", "Test license", chart_type="daily", country="US")

    assert first.valid_rows == 5
    assert second.duplicates_skipped >= 1

    backup_path = tmp_path / "backup.db"
    db.backup_database(backup_path)
    assert backup_path.exists()
    with pytest.raises(ValueError, match="different from the active database"):
        db.backup_database(db.db_path)
    backup_connection = sqlite3.connect(str(backup_path))
    try:
        assert backup_connection.execute(
            "SELECT COUNT(*) FROM chart_records WHERE source = ?", ("Test Source",)
        ).fetchone()[0] == 5
        assert backup_connection.execute("PRAGMA user_version").fetchone()[0] == 1
    finally:
        backup_connection.close()

    restored = DatabaseManager(tmp_path / "restored.db")
    restored.connection.execute("INSERT INTO chart_records (batch_id, source, source_license, chart_type, country, chart_date, position, track_name, artist_names, streams) VALUES ('batch-test', 'restore', 'license', 'daily', 'US', '2024-01-10', 10, 'Restore Song', 'Restore Artist', 1500)")
    restored.connection.commit()
    with pytest.raises(FileExistsError, match="not overwritten"):
        restored.backup_database(backup_path)

    restored.restore_database(backup_path)
    assert restored.get_summary(chart_type="daily")["total_streams"] == 49500
    restored.backup_database(tmp_path / "after_restore_backup.db")

    broken_backup = tmp_path / "broken.db"
    broken_backup.write_text("not a SQLite database", encoding="utf-8")
    with pytest.raises(sqlite3.DatabaseError):
        restored.restore_database(broken_backup)
    assert restored.get_summary(chart_type="daily")["total_streams"] == 49500

def test_empty_database_startup_and_demo_dataset(tmp_path: Path) -> None:
    db = DatabaseManager(tmp_path / "empty.db")
    empty = db.get_summary(chart_type="daily")
    assert empty == {"total_streams": 0, "distinct_tracks": 0, "distinct_artists": 0, "chart_dates_with_data": 0, "coverage_percentage": 0.0}

    batch = db.seed_demo_dataset()
    assert batch
    assert db.get_summary(chart_type="daily")["total_streams"] == 0
    demo = db.get_summary(chart_type="daily", include_demo=True)
    assert demo["total_streams"] > 0
    assert demo["distinct_tracks"] == 6
    assert db.get_summary(chart_type="weekly", include_demo=True)["total_streams"] > 0
    assert db.get_available_date_bounds(
        include_demo=True, chart_type="daily"
    ) == {"earliest": "2017-01-01", "latest": "2024-12-01"}
    assert len(db.get_album_rankings(chart_type="daily", include_demo=True)) == 4
    assert len(db.get_artist_summary(chart_type="daily", include_demo=True)) == 4
    assert db.get_coverage("daily", include_demo=True)["missing_dates"]
    assert db.remove_demo_dataset() > 0
    assert db.get_summary(chart_type="daily", include_demo=True)["total_streams"] == 0


def test_daily_weekly_non_mixing(tmp_path: Path) -> None:
    db = DatabaseManager(tmp_path / "daily_weekly.db")
    daily_rows = [
        ("2024-02-01", "Daily Song A", "Artist One", 5000),
        ("2024-02-02", "Daily Song A", "Artist One", 6000),
    ]
    weekly_rows = [
        ("2024-02-05", "Weekly Song Z", "Artist Weekly", 25000),
        ("2024-02-12", "Weekly Song Z", "Artist Weekly", 31000),
        ("2024-02-26", "Weekly Song Z", "Artist Weekly", 10000),
    ]

    for row in daily_rows:
        db.register_chart_record(
            batch_id="daily-batch",
            source="Daily Source",
            source_license="License",
            chart_type="daily",
            country="US",
            chart_date=row[0],
            weekly_start=None,
            weekly_end=None,
            position=1,
            track_id=f"daily-{row[1]}",
            track_name=row[1],
            artist_names=row[2],
            streams=row[3],
            original_url=None,
        )

    for row in weekly_rows:
        db.register_chart_record(
            batch_id="weekly-batch",
            source="Weekly Source",
            source_license="License",
            chart_type="weekly",
            country="US",
            chart_date=row[0],
            weekly_start=row[0],
            weekly_end=row[0],
            position=1,
            track_id=f"weekly-{row[1]}",
            track_name=row[1],
            artist_names=row[2],
            streams=row[3],
            original_url=None,
        )

    assert db.get_summary(chart_type="daily")["total_streams"] == 11000
    assert db.get_summary(chart_type="weekly")["total_streams"] == 66000
    assert db.get_coverage("weekly")["missing_dates"] == ["2024-02-19"]


def test_country_aliases_are_normalized_and_invalid_ranges_rejected(tmp_path: Path) -> None:
    csv_path = tmp_path / "us_country_aliases.csv"
    csv_path.write_text("Date,Track Name,Artist,Streams\n2024-01-10,Alias Song,Alias Artist,1500\n", encoding="utf-8")

    db = DatabaseManager(tmp_path / "normalized_country.db")
    result = import_csv_file(db, csv_path, "Alias Source", "Alias license", chart_type="daily", country="United States")
    assert result.valid_rows == 1
    assert db.get_summary(chart_type="daily")["total_streams"] == 1500

    with pytest.raises(ValueError, match="start_date must be on or before end_date"):
        db.get_summary(start_date="2024-01-20", end_date="2024-01-10", chart_type="daily")


def test_date_filtering_rank_search_and_song_details(tmp_path: Path) -> None:
    db = DatabaseManager(tmp_path / "filtered.db")
    import_csv_file(db, FIXTURE_CSV, "Test Source", "Test license", chart_type="daily", country="US")

    filtered = db.get_summary(start_date="2024-01-01", end_date="2024-01-01", chart_type="daily")
    assert filtered["total_streams"] == 19000
    assert filtered["chart_dates_with_data"] == 1

    rankings = db.get_top_tracks(limit=50, chart_type="daily")
    assert rankings[0]["track_name"] == "Song A"
    assert rankings[0]["total_streams"] == 34000
    assert rankings[0]["chart_appearances"] == 3
    assert db.get_top_tracks(limit=50, chart_type="daily", search="song b")[0]["track_name"] == "Song B"

    detail = db.get_song_detail(
        track_name="",
        artist_names="",
        chart_type="daily",
        track_key=rankings[0]["track_key"],
    )
    assert detail is not None
    assert detail["total_streams"] == 34000
    assert detail["best_position"] == 1
    assert detail["first_appearance"] == "2024-01-01"
    assert detail["latest_appearance"] == "2024-01-03"
    assert detail["observed_dates"] == 3


def test_coverage_inventory_and_demo_separation(tmp_path: Path) -> None:
    db = DatabaseManager(tmp_path / "coverage.db")
    import_csv_file(db, FIXTURE_CSV, "Test Source", "Test license", chart_type="daily", country="US")
    db.register_chart_record(
        batch_id="gap-batch",
        source="Test Source",
        source_license="Test license",
        chart_type="daily",
        country="US",
        chart_date="2024-01-06",
        weekly_start=None,
        weekly_end=None,
        position=1,
        track_id="gap-track",
        track_name="Gap Song",
        artist_names="Gap Artist",
        streams=2000,
        original_url=None,
    )
    coverage = db.get_coverage("daily")
    assert coverage["earliest"] == "2024-01-01"
    assert coverage["latest"] == "2024-01-06"
    assert coverage["missing_dates"] == ["2024-01-05"]

    db.seed_demo_dataset()
    real = db.get_summary(chart_type="daily")
    combined = db.get_summary(chart_type="daily", include_demo=True)
    assert real["total_streams"] == 51500
    assert combined["total_streams"] > real["total_streams"]
    assert db.get_coverage("daily")["earliest"] == "2024-01-01"
    inventory = db.get_data_inventory()
    assert inventory["summary"]["real_rows"] == 6
    assert inventory["summary"]["demo_rows"] > 5
    assert all(year["year"] == "2024" for year in inventory["years"])


def test_import_without_position_does_not_double_count_and_track_ids_merge(tmp_path: Path) -> None:
    csv_path = tmp_path / "without_position.csv"
    csv_path.write_text(
        "Date,Track Name,Artist,Streams\n"
        "2024-03-01,No Rank Song,No Rank Artist,1200\n"
        "2024-03-01,No Rank Song,No Rank Artist,1200\n",
        encoding="utf-8",
    )
    db = DatabaseManager(tmp_path / "identity.db")
    result = import_csv_file(db, csv_path, "No Rank Source", "Test license")
    assert result.valid_rows == 1
    assert result.duplicates_skipped == 1
    assert db.get_summary()["total_streams"] == 1200


def test_generated_demo_source_name_is_reserved(tmp_path: Path) -> None:
    db = DatabaseManager(tmp_path / "reserved-demo.db")
    with pytest.raises(ValueError, match="reserved for the isolated generated demo fixture"):
        import_csv_file(
            db,
            FIXTURE_CSV,
            "DEMO / SYNTHETIC",
            "Not a demo fixture",
            chart_type="daily",
        )

    for position, name, streams in [(1, "Original title", 2000), (2, "Alternate title", 3000)]:
        db.register_chart_record(
            batch_id="stable-id-batch",
            source="Stable ID Source",
            source_license="Test license",
            chart_type="daily",
            country="US",
            chart_date="2024-03-02",
            weekly_start=None,
            weekly_end=None,
            position=position,
            track_id="same-stable-id",
            track_name=name,
            artist_names="Same Artist",
            streams=streams,
            original_url=None,
        )
    ranked = db.get_top_tracks(chart_type="daily")
    stable_id_rows = [row for row in ranked if row["track_key"] == "same-stable-id"]
    assert len(stable_id_rows) == 1
    assert stable_id_rows[0]["total_streams"] == 5000


def test_chart_import_rolls_back_on_database_failure(tmp_path: Path) -> None:
    db = DatabaseManager(tmp_path / "chart_rollback.db")
    db.connection.execute(
        """
        CREATE TRIGGER reject_chart_record BEFORE INSERT ON chart_records
        BEGIN SELECT RAISE(ABORT, 'fixture chart failure'); END
        """
    )
    db.connection.commit()
    with pytest.raises(sqlite3.IntegrityError, match="fixture chart failure"):
        import_csv_file(db, FIXTURE_CSV, "Rollback Source", "Test license")
    assert db.connection.execute("SELECT COUNT(*) FROM chart_records").fetchone()[0] == 0
    assert db.connection.execute("SELECT COUNT(*) FROM import_batches").fetchone()[0] == 0
    assert db.connection.execute("SELECT COUNT(*) FROM sources WHERE name = 'Rollback Source'").fetchone()[0] == 0
