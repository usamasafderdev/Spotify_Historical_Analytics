from __future__ import annotations

import csv
from datetime import date, timedelta
import gzip
import hashlib
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


def album_weekly(path, rows):
    return write_source(path, ["date", "country", "rank", "uri", "album_name", "artist_names"], rows)


def song_charts(path, rows):
    headers = ["title", "rank", "date", "artist", "url", "region", "chart", "trend", "streams"]
    return write_source(path, headers, rows)


def artist_daily(path, rows):
    headers = [
        "date", "country", "rank", "uri", "artist_name", "peak_rank", "previous_rank",
        "days_on_chart", "consecutive_days", "entry_status", "peak_date", "entry_rank",
        "entry_date",
    ]
    return write_source(path, headers, rows)


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


def test_album_weekly_positions_remain_separate_from_song_streams(db, tmp_path):
    song_path = weekly(tmp_path / "songs.csv.gz", [observation()])
    integrate_file(db, song_path, "weekly")
    album_two = "D" * 22
    path = album_weekly(tmp_path / "charts_albums_weekly.csv", [
        ["2024-02-08", "us", 1, "spotify:album:" + ALBUM, "TEST DATA Album", "TEST DATA Artist"],
        ["2024-02-08", "us", 1, "spotify:album:" + ALBUM, "TEST DATA Album", "TEST DATA Artist"],
        ["2024-02-08", "us", 2, "spotify:album:" + ALBUM, "TEST DATA Album", "TEST DATA Artist"],
        ["2024-02-08", "us", 2, "spotify:album:" + album_two, "TEST DATA Album Two", "TEST DATA Artist"],
        ["2024-02-08", "us", 2, "spotify:album:" + album_two, "TEST DATA Album Two", "TEST DATA Artist"],
        ["2024-02-08", "ca", 1, "spotify:album:" + album_two, "TEST DATA Album Two", "TEST DATA Artist"],
    ])

    result = integrate_file(db, path, "album_weekly")

    assert result["imported_rows"] == result["album_records_added"] == 1
    assert result["duplicates"] == 1
    assert result["conflicts"] == 3
    assert result["excluded_non_us"] == 1
    assert result["stream_column_present"] is False
    records = db.get_album_chart_records()
    assert [(row["album_id"], row["position"], row["weekly_start"], row["weekly_end"])
            for row in records] == [(album_two, 2, "2024-02-02", "2024-02-08")]
    assert db.connection.execute("SELECT COUNT(*) FROM chart_records").fetchone()[0] == 1
    assert db.connection.execute("SELECT COUNT(*) FROM track_albums").fetchone()[0] == 0
    assert db.get_summary(chart_type="weekly")["total_streams"] == 100


def test_artist_listener_metrics_are_separate_and_conflicts_preserve_existing(db, tmp_path):
    db.upsert_artist(ARTIST, "TEST DATA Artist")
    path = write_source(tmp_path / "artist_listeners_daily.csv",
                        ["artist_id", "date", "listeners"],
                        [[ARTIST, "2024-02-08", 1000], [ARTIST, "2024-02-08", 1000]])

    result = integrate_file(db, path, "artist_listener_metrics")

    assert result["imported_rows"] == result["listener_records_added"] == 1
    assert result["duplicates"] == 1
    assert result["conflicts"] == 0
    assert db.get_artist_listener_history(ARTIST) == [{"date": "2024-02-08", "listeners": 1000}]
    assert db.get_summary(chart_type="weekly")["total_streams"] == 0

    changed = write_source(tmp_path / "artist_listeners_daily.csv",
                           ["artist_id", "date", "listeners"],
                           [[ARTIST, "2024-02-08", 2000]])
    result = integrate_file(db, changed, "artist_listener_metrics")
    assert result["imported_rows"] == 0
    assert result["conflicts"] == 1
    assert db.get_artist_listener_history(ARTIST) == [{"date": "2024-02-08", "listeners": 1000}]


def test_daily_top200_import_keeps_verified_tracks_and_streams_separate(db, tmp_path):
    second_track = "D" * 22
    path = song_charts(tmp_path / "charts.csv", [
        ["TEST DATA Song", 1, "2024-02-08", "TEST DATA Artist", "https://open.spotify.com/track/" + TRACK, "United States", "top200", "SAME_POSITION", 1000],
        ["TEST DATA Song", 1, "2024-02-08", "TEST DATA Artist", "https://open.spotify.com/track/" + TRACK, "United States", "top200", "SAME_POSITION", 1000],
        ["TEST DATA Song", 1, "2024-02-08", "TEST DATA Artist", "https://open.spotify.com/track/" + TRACK, "United States", "top200", "SAME_POSITION", 1001],
        ["TEST DATA Song Two", 2, "2024-02-08", "Other Artist", "https://open.spotify.com/track/" + second_track, "United States", "top200", "NEW_ENTRY", 500],
        ["TEST DATA Song Two", 2, "2024-02-08", "Other Artist", "https://open.spotify.com/track/" + second_track, "United States", "top200", "NEW_ENTRY", 500],
        ["Viral Song", 1, "2024-02-08", "Viral Artist", "https://open.spotify.com/track/" + ("E" * 22), "United States", "viral50", "NEW_ENTRY", 50],
        ["Canada Song", 1, "2024-02-08", "Canada Artist", "https://open.spotify.com/track/" + ("F" * 22), "Canada", "top200", "NEW_ENTRY", 75],
    ])

    result = integrate_file(db, path, "chart_csv_daily")

    assert result["imported_rows"] == 1
    stored_hash = db.connection.execute(
        "SELECT sha256 FROM integration_files WHERE path=?", (str(path.resolve()),)
    ).fetchone()[0]
    assert stored_hash == hashlib.sha256(path.read_bytes()).hexdigest()
    assert result["duplicates"] == 1
    assert result["conflicts"] == 3
    assert result["excluded_other_chart"] == 1
    assert result["excluded_non_us"] == 1
    assert result["stream_column_present"] is True
    assert db.connection.execute("SELECT COUNT(*) FROM chart_records").fetchone()[0] == 1
    row = db.connection.execute("SELECT chart_type,track_id,streams,original_url FROM chart_records").fetchone()
    assert tuple(row) == ("daily", second_track, 500, "https://open.spotify.com/track/" + second_track)
    assert db.get_summary(chart_type="daily")["total_streams"] == 500
    assert db.get_summary(chart_type="weekly")["total_streams"] == 0
    assert db.connection.execute("SELECT COUNT(*) FROM track_artists").fetchone()[0] == 0


def test_native_daily_songs_and_overlapping_source_preserve_established_values(db, tmp_path):
    path = write_source(tmp_path / "charts_songs_daily.csv",
        ["date", "country", "rank", "uri", "artist_names", "track_name", "streams", "artist_uris"], [
            ["2024-02-08", "us", 1, "spotify:track:" + TRACK, "TEST DATA Artist", "TEST DATA Song", 1000, "spotify:artist:" + ARTIST],
            ["2024-02-09", "us", 2, "spotify:track:" + TRACK, "TEST DATA Artist", "TEST DATA Song", 2000, "spotify:artist:" + ARTIST],
            ["2024-02-08", "global", 1, "spotify:track:" + TRACK, "TEST DATA Artist", "TEST DATA Song", 999999, "spotify:artist:" + ARTIST],
            ["2024-02-10", "us", 1, "spotify:track:" + TRACK, "TEST DATA Artist", "TEST DATA Song", -1, "spotify:artist:" + ARTIST],
        ])
    result = integrate_file(db, path, "native_song_daily")
    assert result["imported_rows"] == 2
    assert result["invalid_rows"] == result["excluded_non_us"] == 1
    assert db.get_summary()["total_streams"] == 3000
    assert db.get_summary(chart_type="weekly")["total_streams"] == 0
    assert db.get_summary(chart_type="weekly_derived")["total_streams"] == 3000
    assert db.get_top_tracks()[0]["chart_appearances"] == 2
    overlap = song_charts(tmp_path / "overlap.csv", [
        ["TEST DATA Song", 1, "2024-02-08", "TEST DATA Artist", "https://open.spotify.com/track/" + TRACK, "United States", "top200", "SAME_POSITION", 1000],
        ["TEST DATA Song", 2, "2024-02-09", "TEST DATA Artist", "https://open.spotify.com/track/" + TRACK, "United States", "top200", "SAME_POSITION", 9999],
        ["TEST DATA Song", 1, "2024-02-08", "TEST DATA Artist", "https://open.spotify.com/track/" + "Z" * 22, "United States", "top200", "SAME_POSITION", 1000],
    ])
    result = integrate_file(db, overlap, "chart_csv_daily")
    assert result["duplicates"] == 1 and result["conflicts"] == 2
    assert result["slot_conflicts"] == 1
    assert db.connection.execute("SELECT incoming_track_id FROM integration_slot_conflicts").fetchone()[0] == "Z" * 22
    assert db.get_summary()["total_streams"] == 3000
    assert db.connection.execute("SELECT incoming_streams FROM integration_conflicts").fetchone()[0] == 9999


def test_daily_artist_positions_are_separate_and_do_not_create_artist_links(db, tmp_path):
    second_artist = "C" * 22
    source_row = ["2024-02-08", "us", 1, "spotify:artist:" + ARTIST, "Chart Artist", 1, -1, 1, 1, "NEW_ENTRY", "2024-02-08", 1, "2024-02-08"]
    changed_row = ["2024-02-08", "us", 2, "spotify:artist:" + ARTIST, "Chart Artist", 1, 1, 2, 1, "MOVED_DOWN", "2024-02-08", 1, "2024-02-08"]
    other_row = ["2024-02-08", "us", 2, "spotify:artist:" + second_artist, "Other Chart Artist", 2, -1, 1, 1, "NEW_ENTRY", "2024-02-08", 2, "2024-02-08"]
    path = artist_daily(tmp_path / "charts_artists_daily.csv", [
        source_row, source_row, changed_row, other_row, other_row,
        ["2024-02-08", "ca", 1, "spotify:artist:" + second_artist, "Other Chart Artist", 1, -1, 1, 1, "NEW_ENTRY", "2024-02-08", 1, "2024-02-08"],
    ])
    db.upsert_artist(ARTIST, "Existing Metadata Name")

    result = integrate_file(db, path, "artist_chart_daily")

    assert result["imported_rows"] == result["artist_chart_records_added"] == 1
    assert result["duplicates"] == 1
    assert result["conflicts"] == 3
    assert result["excluded_non_us"] == 1
    assert db.connection.execute("SELECT COUNT(*) FROM chart_records").fetchone()[0] == 0
    assert db.connection.execute("SELECT COUNT(*) FROM track_artists").fetchone()[0] == 0
    assert db.connection.execute(
        "SELECT artist_name FROM artists WHERE artist_id=?", (ARTIST,)
    ).fetchone()[0] == "Existing Metadata Name"
    records = db.get_artist_chart_records(artist_id=second_artist)
    assert [(row["artist_id"], row["position"], row["artist_name"]) for row in records] == [
        (second_artist, 2, "Other Chart Artist")
    ]


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


def test_cli_manifest_integrates_album_charts_and_listener_metrics(tmp_path, monkeypatch):
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    target = tmp_path / "isolated"
    write_source(downloads / "artists.csv", ["artist_uri", "artist_name"], [["spotify:artist:" + ARTIST, "TEST DATA Artist"]])
    album_weekly(downloads / "charts_albums_weekly.csv", [
        ["2024-02-08", "us", 1, "spotify:album:" + ALBUM, "TEST DATA Album", "TEST DATA Artist"],
    ])
    write_source(downloads / "artist_listeners_daily.csv",
                 ["artist_id", "date", "listeners"], [[ARTIST, "2024-02-08", 99999]])
    artist_daily(downloads / "charts_artists_daily.csv", [
        ["2024-02-08", "us", 1, "spotify:artist:" + ARTIST, "TEST DATA Artist", 1, -1, 1, 1, "NEW_ENTRY", "2024-02-08", 1, "2024-02-08"],
    ])
    nested_charts = downloads / "charts.csv"
    nested_charts.mkdir()
    song_charts(nested_charts / "charts.csv", [
        ["TEST DATA Song", 1, "2024-02-08", "TEST DATA Artist", "https://open.spotify.com/track/" + TRACK, "United States", "top200", "NEW_ENTRY", 100],
    ])
    monkeypatch.setattr("sys.argv", ["integration", "--downloads", str(downloads), "--data-dir", str(target)])
    assert integration_main() == 0

    def unexpected_read(path):
        raise AssertionError("Unchanged source should not be reopened")

    monkeypatch.setattr("spotify_historical_analytics.local_integration.locked_source", unexpected_read)
    assert integration_main() == 0
    report = json.loads((target / "source-manifest.json").read_text())
    assert len(report["files"]) == 5
    assert next(row for row in report["files"] if row["category"] == "artist_listener_metrics")["status"] == "complete"
    assert next(row for row in report["files"] if row["category"] == "album_weekly")["status"] == "complete"
    assert next(row for row in report["files"] if row["category"] == "artist_chart_daily")["status"] == "complete"
    assert next(row for row in report["files"] if row["category"] == "chart_csv_daily")["status"] == "complete"


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
