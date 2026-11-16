from __future__ import annotations

import csv
from datetime import date, timedelta
import gzip
import json
import os
import time

import pytest

from spotify_historical_analytics.db import DatabaseManager
from spotify_historical_analytics.local_integration import initialize, integrate_file, locked_source
from spotify_historical_analytics.local_integration import main as integration_main
from spotify_historical_analytics.services.appearances import chart_showings
from spotify_historical_analytics.services.references import entity_references


TRACK = "A" * 22
ARTIST = "B" * 22
ALBUM = "C" * 22


def write_source(path, headers, rows):
    opener = gzip.open if path.name.endswith(".gz") else open
    with opener(path, "wt", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(headers)
        writer.writerows(rows)
    os.utime(path, (time.time() - 120, time.time() - 120))
    return path


@pytest.fixture
def db(tmp_path):
    database = DatabaseManager(tmp_path / "TEST-DATA.db")
    initialize(database)
    yield database
    database.close()


def metadata(db, tmp_path):
    sources = [
        ("artists.csv", "artist", ["artist_uri", "artist_name", "monthly_listeners"], [["spotify:artist:" + ARTIST, "TEST DATA Artist", 999999]]),
        ("albums.csv", "album", ["album_uri", "album_name", "artist_names", "artist_uris"], [["spotify:album:" + ALBUM, "TEST DATA Album", "TEST DATA Artist", "spotify:artist:" + ARTIST]]),
        ("songs.csv", "track", ["track_uri", "track_name", "artist_names", "artist_uris", "all_uris"], [["spotify:track:" + TRACK, "TEST DATA Song", "TEST DATA Artist", "spotify:artist:" + ARTIST, "spotify:track:" + TRACK]]),
        ("artwork.csv", "artwork", ["uri", "type", "image_url"], [["spotify:track:" + TRACK, "song", "https://i.scdn.co/image/TEST-DATA"]]),
        ("links.csv", "links", ["spotify_uri", "type", "youtube_video_id"], [["spotify:track:" + TRACK, "song", "TEST-DATA"]]),
    ]
    for filename, category, headers, rows in sources:
        path = write_source(tmp_path / filename, headers, rows)
        integrate_file(db, path, category)


def weekly(path, rows):
    return write_source(path, ["cc", "week_end", "rank", "streams", "track_id", "title", "artists", "artist_uris"], rows)


def observation(streams=100, country="us", end="2024-02-08", position=1, track=TRACK):
    return [country, end, position, streams, track, "TEST DATA Song", "TEST DATA Artist", "spotify:artist:" + ARTIST]


def test_metadata_exact_joins_and_references_without_invented_streams(db, tmp_path):
    metadata(db, tmp_path)
    assert db.connection.execute("SELECT COUNT(*) FROM track_artists").fetchone()[0] == 1
    assert db.connection.execute("SELECT COUNT(*) FROM album_artists").fetchone()[0] == 1
    assert db.connection.execute("SELECT COUNT(*) FROM track_albums").fetchone()[0] == 0
    assert db.get_summary()["total_streams"] == 0
    assert len(entity_references(db, "track", TRACK)) == 2
    assert json.loads(db.connection.execute("SELECT payload_json FROM entity_metadata WHERE entity_type='artist'").fetchone()[0])["monthly_listeners"] == "999999"


def test_weekly_insertion_market_validation_separation_repeat_and_persistence(db, tmp_path):
    metadata(db, tmp_path)
    path = weekly(tmp_path / "weekly.csv.gz", [observation(), observation(200, end="2024-02-15"), observation(999, country="global")])
    result = integrate_file(db, path, "weekly")
    assert result["imported_rows"] == 2 and result["excluded_non_us"] == 1
    assert db.get_summary(chart_type="weekly")["total_streams"] == 300
    assert db.get_summary()["total_streams"] == 0
    assert db.get_summary(chart_type="weekly_derived")["total_streams"] == 0
    assert db.get_artist_summary(chart_type="weekly")[0]["charting_song_streams"] == 300
    assert db.get_top_tracks(chart_type="weekly")[0]["chart_appearances"] == 2
    assert len(chart_showings(db, "songs", chart_type="weekly")) == 2
    assert len(chart_showings(db, "songs", chart_type="weekly", hide_repeats=True)) == 1
    reopened = DatabaseManager(db.db_path)
    try:
        assert reopened.get_summary(chart_type="weekly")["total_streams"] == 300
    finally:
        reopened.close()


def test_duplicates_conflicts_and_unchanged_manifest(db, tmp_path):
    first = weekly(tmp_path / "one.csv.gz", [observation(), observation()])
    result = integrate_file(db, first, "weekly")
    assert (result["imported_rows"], result["duplicates"]) == (1, 1)
    assert integrate_file(db, first, "weekly")["status"] == "unchanged"
    second = weekly(tmp_path / "two.csv.gz", [observation(999), observation(position=2)])
    result = integrate_file(db, second, "weekly")
    assert result["conflicts"] == 2 and result["imported_rows"] == 0
    assert db.get_summary(chart_type="weekly")["total_streams"] == 100


@pytest.mark.parametrize("row", [observation(-1), observation("1.5"), observation("NaN"), observation(str(2**63)),
                                 observation(end="2024-02-09"), observation(track="bad-id"), observation(position=0)])
def test_invalid_chart_values_do_not_enter_database(db, tmp_path, row):
    path = weekly(tmp_path / "invalid.csv.gz", [row])
    result = integrate_file(db, path, "weekly")
    assert result["invalid_rows"] == 1
    assert db.connection.execute("SELECT COUNT(*) FROM chart_records").fetchone()[0] == 0


def test_metadata_name_conflict_preserves_original(db, tmp_path):
    metadata(db, tmp_path)
    path = write_source(tmp_path / "conflict.csv", ["artist_uri", "artist_name"], [["spotify:artist:" + ARTIST, "TEST DATA changed name"]])
    result = integrate_file(db, path, "artist")
    assert result["conflicts"] == 1
    assert db.connection.execute("SELECT artist_name FROM artists WHERE artist_id=?", (ARTIST,)).fetchone()[0] == "TEST DATA Artist"


def test_file_schema_failure_rolls_back(db, tmp_path):
    path = write_source(tmp_path / "bad.csv", ["cc", "week_end"], [["us", "2024-02-08"]])
    with pytest.raises(ValueError, match="schema"):
        integrate_file(db, path, "weekly")
    assert db.connection.execute("SELECT COUNT(*) FROM integration_files").fetchone()[0] == 0


def test_recent_or_actively_written_sources_are_not_read(tmp_path):
    path = tmp_path / "TEST-DATA.csv"
    path.write_text("TEST DATA")
    with pytest.raises(ValueError, match="recently"):
        with locked_source(path):
            pass
    os.utime(path, (time.time() - 120, time.time() - 120))
    if os.name == "nt":
        with path.open("ab"):
            with pytest.raises(OSError, match="active writers"):
                with locked_source(path):
                    pass


def test_cli_refuses_existing_user_database(tmp_path, monkeypatch):
    target = tmp_path / "user-data"
    db = DatabaseManager(target / "database" / "analytics.db")
    db.close()
    before = (target / "database" / "analytics.db").read_bytes()
    monkeypatch.setattr("sys.argv", ["integration", "--downloads", str(tmp_path), "--data-dir", str(target)])
    with pytest.raises(ValueError, match="existing user database"):
        integration_main()
    assert (target / "database" / "analytics.db").read_bytes() == before


def test_cli_manifest_skips_unchanged_and_excludes_listener_metric(tmp_path, monkeypatch):
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    target = tmp_path / "isolated"
    write_source(downloads / "artists.csv", ["artist_uri", "artist_name"], [["spotify:artist:" + ARTIST, "TEST DATA Artist"]])
    (downloads / "artist_listeners_daily.csv").write_text("artist_id,date,listeners\nTEST DATA,2024-01-01,99999\n")
    monkeypatch.setattr("sys.argv", ["integration", "--downloads", str(downloads), "--data-dir", str(target)])
    assert integration_main() == 0
    def unexpected_read(path):
        raise AssertionError("Unchanged source should not be reopened")
    monkeypatch.setattr("spotify_historical_analytics.local_integration.locked_source", unexpected_read)
    assert integration_main() == 0
    report = json.loads((target / "source-manifest.json").read_text())
    assert len(report["files"]) == 2
    assert next(row for row in report["files"] if row["category"] == "artist_listener_metrics")["status"] == "excluded"


def test_cli_skips_recent_source_and_processes_other_completed_files(tmp_path, monkeypatch):
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    target = tmp_path / "isolated"
    (downloads / "artists.csv").write_text("artist_uri,artist_name\n")
    write_source(downloads / "albums.csv", ["album_uri", "album_name"], [["spotify:album:" + ALBUM, "TEST DATA Album"]])
    monkeypatch.setattr("sys.argv", ["integration", "--downloads", str(downloads), "--data-dir", str(target)])
    assert integration_main() == 0
    report = json.loads((target / "source-manifest.json").read_text())
    assert report["skipped_files"][0]["file"] == "artists.csv"
    assert len(report["files"]) == 1
