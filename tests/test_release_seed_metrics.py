from __future__ import annotations

import sqlite3

import pytest

from spotify_historical_analytics.db import DatabaseManager
from spotify_historical_analytics.runtime import initialize_release_seed
from spotify_historical_analytics.services.appearances import chart_showings


def test_release_seed_copies_once_and_preserves_user_updates(tmp_path):
    seed = tmp_path / "seed.sqlite"
    with sqlite3.connect(seed) as connection:
        connection.execute("CREATE TABLE retained(value TEXT)")
        connection.execute("INSERT INTO retained VALUES ('genuine seed')")
    destination = tmp_path / "profile" / "analytics.db"
    assert initialize_release_seed(destination, seed)
    with sqlite3.connect(destination) as connection:
        connection.execute("INSERT INTO retained VALUES ('user import')")
    assert not initialize_release_seed(destination, seed)
    with sqlite3.connect(destination) as connection:
        assert connection.execute("SELECT COUNT(*) FROM retained").fetchone()[0] == 2
    assert not list(destination.parent.glob(".seed-*"))


def test_broken_release_seed_does_not_create_user_database(tmp_path):
    seed = tmp_path / "broken.sqlite"
    seed.write_text("broken")
    destination = tmp_path / "profile" / "analytics.db"
    with pytest.raises(sqlite3.DatabaseError):
        initialize_release_seed(destination, seed)
    assert not destination.exists()
    assert not list(destination.parent.glob(".seed-*"))


def test_read_only_analytics_never_accepts_persistent_writes(tmp_path):
    destination = tmp_path / "analytics.sqlite"
    DatabaseManager(destination).close()
    db = DatabaseManager(destination, read_only=True)
    try:
        assert db.get_summary()["total_streams"] == 0
        with pytest.raises(sqlite3.OperationalError, match="readonly"):
            db.connection.execute("INSERT INTO artists(artist_id) VALUES ('TEST DATA')")
    finally:
        db.close()


@pytest.mark.parametrize("category,source", [
    ("artists", "artist_positions"), ("albums", "album_positions"), ("artists", "listeners"),
])
def test_separate_metric_showings_count_before_limit_without_invented_streams(tmp_path, category, source):
    db = DatabaseManager(tmp_path / "metrics.sqlite")
    try:
        for day in range(1, 5):
            for identity in ["A" * 22, "B" * 22]:
                reporting_date = f"2024-01-0{day}"
                if source == "listeners":
                    db.connection.execute("INSERT INTO artist_listener_records(artist_id,metric_date,listeners,source) VALUES (?,?,?,?)", (identity, reporting_date, day * 100, "TEST DATA"))
                else:
                    table, field = ("artist_chart_records", "artist") if category == "artists" else ("album_chart_records", "album")
                    cadence = "daily" if category == "artists" else "weekly"
                    if category == "albums":
                        db.connection.execute("INSERT INTO album_chart_records(album_id,album_name,chart_date,country,chart_type,position,source,batch_id,weekly_start,weekly_end,artist_names) VALUES (?,?,?,'US','weekly',?,'TEST DATA','TEST DATA',?,?,'TEST DATA')", (identity, "TEST DATA", reporting_date, day, reporting_date, reporting_date))
                    else:
                        db.connection.execute("INSERT INTO artist_chart_records(artist_id,artist_name,chart_date,country,chart_type,position,source,batch_id) VALUES (?,?,?,'US','daily',?,'TEST DATA','TEST DATA')", (identity, "TEST DATA", reporting_date, day))
        db.connection.commit()
        rows = chart_showings(db, category, source=source, limit=2, sort="newest")
        assert len(rows) == 2
        assert all(row["chart_appearances"] == 4 and row["streams"] is None for row in rows)
        rows = chart_showings(db, category, source=source, limit=2, sort="newest", hide_repeats=True)
        assert len({row["entity_id"] for row in rows}) == 2
        assert all(row["chart_date"] == "2024-01-04" for row in rows)
        assert db.connection.execute("SELECT COUNT(*) FROM chart_records").fetchone()[0] == 0
    finally:
        db.close()
