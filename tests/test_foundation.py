from __future__ import annotations

from pathlib import Path

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


def test_duplicate_imports_and_backup_restore(tmp_path: Path) -> None:
    db = DatabaseManager(tmp_path / "dup.db")
    first = import_csv_file(db, FIXTURE_CSV, "Test Source", "Test license", chart_type="daily", country="US")
    second = import_csv_file(db, FIXTURE_CSV, "Test Source", "Test license", chart_type="daily", country="US")

    assert first.valid_rows == 5
    assert second.duplicates_skipped >= 1

    backup_path = tmp_path / "backup.db"
    db.backup_database(backup_path)
    assert backup_path.exists()

    restored = DatabaseManager(tmp_path / "restored.db")
    restored.connection.execute("INSERT INTO chart_records (batch_id, source, source_license, chart_type, country, chart_date, position, track_name, artist_names, streams) VALUES ('batch-test', 'restore', 'license', 'daily', 'US', '2024-01-10', 10, 'Restore Song', 'Restore Artist', 1500)")
    restored.connection.commit()

    restored.backup_database(tmp_path / "after_restore_backup.db")


def test_empty_database_startup_and_demo_dataset(tmp_path: Path) -> None:
    db = DatabaseManager(tmp_path / "empty.db")
    empty = db.get_summary(chart_type="daily")
    assert empty == {"total_streams": 0, "distinct_tracks": 0, "distinct_artists": 0, "chart_dates_with_data": 0, "coverage_percentage": 0.0}

    batch = db.seed_demo_dataset()
    assert batch
    demo = db.get_summary(chart_type="daily", include_demo=True)
    assert demo["total_streams"] == 591000
    assert demo["distinct_tracks"] == 3


def test_daily_weekly_non_mixing(tmp_path: Path) -> None:
    db = DatabaseManager(tmp_path / "daily_weekly.db")
    daily_rows = [
        ("2024-02-01", "Daily Song A", "Artist One", 5000),
        ("2024-02-02", "Daily Song A", "Artist One", 6000),
    ]
    weekly_rows = [
        ("2024-02-05", "Weekly Song Z", "Artist Weekly", 25000),
        ("2024-02-12", "Weekly Song Z", "Artist Weekly", 31000),
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
    assert db.get_summary(chart_type="weekly")["total_streams"] == 56000
