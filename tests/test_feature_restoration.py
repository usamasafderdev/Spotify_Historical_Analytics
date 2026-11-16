from __future__ import annotations

import csv
import gzip
import math
import os
import sqlite3

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from openpyxl import Workbook, load_workbook
import pytest
from PySide6.QtWidgets import QApplication

from spotify_historical_analytics.db import DatabaseManager
from spotify_historical_analytics.exports import export_rankings
from spotify_historical_analytics.ui.history_chart import history_points, observation_timestamp, render_history
from spotify_historical_analytics.ui.main_window import ChartPanel, MainWindow
from spotify_historical_analytics.ui.workers import DashboardQueryWorker
from spotify_historical_analytics.weekly_import import import_weekly_files


@pytest.fixture
def database(tmp_path):
    db = DatabaseManager(tmp_path / "TEST-DATA.db")
    for track, day, streams in [
        ("A", "2024-01-01", 100), ("A", "2024-01-02", 200),
        ("A", "2024-01-04", 50), ("A", "2024-01-09", 10),
        ("B", "2024-01-01", 70), ("B", "2024-01-09", 20),
    ]:
        add_observation(db, track * 22, day, streams)
    add_observation(db, "A" * 22, "2024-01-01", 100, source="TEST DATA duplicate source")
    add_observation(db, "A" * 22, "2024-01-07", 999, cadence="weekly")
    db.connection.execute("INSERT INTO artists(artist_id,artist_name) VALUES ('artist-id','TEST DATA Artist')")
    db.connection.execute("INSERT INTO albums(album_id,album_name) VALUES ('album-id','TEST DATA Album')")
    for track in ("A" * 22, "B" * 22):
        db.connection.execute("INSERT INTO track_artists(track_id,artist_id,mapping_status) VALUES (?,'artist-id','id_match')", (track,))
        db.connection.execute("INSERT INTO track_albums(track_id,album_id,mapping_status) VALUES (?,'album-id','id_match')", (track,))
    db.connection.commit()
    yield db
    db.close()


def add_observation(db, track, day, streams, source="TEST DATA", cadence="daily"):
    db.register_chart_record(
        batch_id="TEST DATA", source=source, source_license="TEST DATA only", chart_type=cadence,
        country="US", chart_date=day, weekly_start="2024-01-01" if cadence == "weekly" else None,
        weekly_end="2024-01-07" if cadence == "weekly" else None, position=1 if track.startswith("A") else 2,
        track_id=track, track_name="TEST DATA identical title", artist_names="TEST DATA Artist", streams=streams,
        original_url=None,
    )


def test_daily_source_weekly_and_derived_queries(database):
    assert database.get_summary()["total_streams"] == 450
    assert database.get_summary(chart_type="weekly")["total_streams"] == 999
    summary = database.get_summary(chart_type="weekly_derived")
    assert summary["total_streams"] == 450
    assert summary["distinct_tracks"] == 2
    assert summary["distinct_artist_entities"] == summary["distinct_albums"] == 1
    assert summary["chart_dates_with_data"] == 2
    assert database.get_available_date_bounds(chart_type="weekly_derived") == {"earliest": "2024-01-07", "latest": "2024-01-14"}
    assert "weekly_derived" in database.get_chart_type_availability()
    assert database.get_summary("2024-01-14", "2024-01-14", chart_type="weekly_derived")["total_streams"] == 30
    assert database.get_top_tracks(chart_type="weekly_derived")[0]["best_position"] == 1
    rows = database.get_streams_over_time(chart_type="weekly_derived", track_key="A" * 22)
    assert [(row["streams"], row["observed_days"]) for row in rows] == [(350, 3), (10, 1)]
    assert database.get_song_detail("", "", track_key="A" * 22, chart_type="weekly_derived")["total_streams"] == 360
    assert database.get_artist_detail("id:artist-id", chart_type="weekly_derived")["charting_song_streams"] == 450
    assert database.get_album_detail("album-id", chart_type="weekly_derived")["charting_track_streams"] == 450


def test_repeats_use_full_filtered_history_and_distinct_identities(database):
    tracks = database.get_top_tracks(limit=1)
    assert tracks[0]["chart_appearances"] == 4
    assert len(database.get_top_tracks()) == 2
    assert database.get_artist_summary()[0]["chart_appearances"] == 4
    assert database.get_album_rankings()[0]["chart_appearances"] == 4
    assert database.get_artist_summary("2024-01-09", "2024-01-09")[0]["chart_appearances"] == 1
    assert database.get_album_rankings(chart_type="weekly_derived")[0]["chart_appearances"] == 2
    assert database.get_top_tracks(search="identical", chart_type="weekly")[0]["chart_appearances"] == 1


HEADERS = ["Date", "Track Name", "Artist", "Streams", "Region", "Position", "Track ID", "Weekly Start", "Weekly End"]


def write_weekly(path, streams=123, track="C" * 22, region="US", end="2024-02-11"):
    rows = [HEADERS, ["2024-02-11", "TEST DATA weekly song", "TEST DATA artist", streams, region, 1, track, "2024-02-05", end]]
    if path.suffix == ".xlsx":
        book = Workbook()
        for row in rows:
            book.active.append(row)
        book.save(path)
        book.close()
    else:
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "wt", newline="", encoding="utf-8") as handle:
            csv.writer(handle).writerows(rows)


@pytest.mark.parametrize("suffix", [".csv", ".csv.gz", ".xlsx"])
def test_weekly_import_duplicate_conflict_and_restart(tmp_path, suffix):
    db = DatabaseManager(tmp_path / "weekly.db")
    path = tmp_path / ("TEST-DATA" + suffix)
    write_weekly(path)
    try:
        results = import_weekly_files(db, [path, path])
        assert [row["imported_rows"] for row in results] == [1, 0]
        assert results[1]["duplicates_skipped"] == 1
        write_weekly(path, streams=456)
        assert "conflict" in import_weekly_files(db, [path])[0]["error"].lower()
        assert db.get_summary()["total_streams"] == 0
        assert db.get_summary(chart_type="weekly")["total_streams"] == 123
    finally:
        db.close()
    reopened = DatabaseManager(tmp_path / "weekly.db")
    try:
        assert reopened.get_summary(chart_type="weekly")["total_streams"] == 123
    finally:
        reopened.close()


@pytest.mark.parametrize("options", [dict(streams=-1), dict(streams="1.5"), dict(streams="NaN"), dict(streams=str(2**63)), dict(track="invalid"), dict(region="CA"), dict(end="2024-02-12")])
def test_invalid_weekly_file_leaves_no_records(tmp_path, options):
    db = DatabaseManager(tmp_path / "invalid.db")
    path = tmp_path / "TEST-DATA.csv"
    write_weekly(path, **options)
    try:
        result = import_weekly_files(db, [path])[0]
        assert result["status"] == "Failed"
        assert db.connection.execute("SELECT COUNT(*) FROM chart_records").fetchone()[0] == 0
        assert db.connection.execute("SELECT COUNT(*) FROM import_batches").fetchone()[0] == 0
    finally:
        db.close()


def test_cross_source_weekly_conflicts_are_atomic(database, tmp_path):
    path = tmp_path / "TEST-DATA.csv"
    write_weekly(path, track="A" * 22)
    with path.open("a", newline="", encoding="utf-8") as handle:
        csv.writer(handle).writerow(["2024-02-11", "TEST DATA new song", "TEST DATA artist", 500, "US", 2, "D" * 22, "2024-02-05", "2024-02-11"])
    add_observation(database, "A" * 22, "2024-02-11", 222, source="Another TEST DATA source", cadence="weekly")
    before = database.connection.execute("SELECT COUNT(*) FROM chart_records").fetchone()[0]
    assert import_weekly_files(database, [path])[0]["status"] == "Failed"
    assert database.connection.execute("SELECT COUNT(*) FROM chart_records").fetchone()[0] == before


@pytest.mark.parametrize("category", ["songs", "artists", "albums"])
@pytest.mark.parametrize("suffix", [".csv", ".xlsx"])
def test_filtered_derived_exports(database, tmp_path, category, suffix):
    path = tmp_path / (category + suffix)
    expected = 2 if category == "songs" else 1
    assert export_rankings(database, category, path, "2024-01-14", "2024-01-14", "weekly_derived", 50) == expected
    if suffix == ".xlsx":
        book = load_workbook(path, read_only=True, data_only=True)
        try:
            rows = list(book["Rankings"].values)
            assert len(rows) == expected + 1
            stream_index = {"songs": 3, "artists": 3, "albums": 4}[category]
            assert sum(row[stream_index] for row in rows[1:]) == 30
            assert "TEST DATA" in dict(list(book["Definitions"].values)[1:])["Source names"]
        finally:
            book.close()
    else:
        assert "weekly_derived" in path.read_text(encoding="utf-8-sig")
        assert "TEST DATA" in path.read_text(encoding="utf-8-sig")


def test_weekly_header_validation(tmp_path):
    db = DatabaseManager(tmp_path / "headers.db")
    try:
        for header in ["Date,Streams\n", "Date,Date,Track Name,Artist,Streams,Region,Track ID\n"]:
            path = tmp_path / "bad-header.csv"
            path.write_text(header, encoding="utf-8")
            assert import_weekly_files(db, [path])[0]["status"] == "Failed"
        assert db.get_summary(chart_type="weekly")["total_streams"] == 0
    finally:
        db.close()


@pytest.mark.parametrize("cadence,total", [("daily", 450), ("weekly", 999), ("weekly_derived", 450)])
def test_dashboard_payload_and_empty_state(database, tmp_path, cadence, total):
    for path, expected in [(database.db_path, total), (tmp_path / "empty.db", 0)]:
        worker = DashboardQueryWorker(str(path), 1, None, None, cadence, "", "", "", 50, 50, 50)
        payloads = []
        errors = []
        worker.completed.connect(payloads.append)
        worker.failed.connect(errors.append)
        worker.run()
        assert not errors
        assert payloads[0]["overview"]["summary"]["total_streams"] == expected
        assert bool(payloads[0]["songs"]) == bool(expected)
        assert bool(payloads[0]["streams"]) == bool(expected)


def test_backup_restore_rejects_unrelated_database(database, tmp_path):
    backup = database.backup_database(tmp_path / "backup.db")
    add_observation(database, "A" * 22, "2024-01-15", 200)
    database.restore_database(backup)
    assert database.get_summary()["total_streams"] == 450
    bad = tmp_path / "unrelated.db"
    with sqlite3.connect(bad) as connection:
        connection.execute("CREATE TABLE unrelated(value TEXT)")
    with pytest.raises(ValueError, match="analytics database"):
        database.restore_database(bad)
    assert database.get_summary()["total_streams"] == 450


def test_history_dates_gaps_zero_baseline_and_repeat_controls(database, monkeypatch, tmp_path):
    monkeypatch.setattr("spotify_historical_analytics.settings.SETTINGS_PATH", tmp_path / "settings.json")
    app = QApplication.instance() or QApplication([])
    rows = [{"chart_date": "2024-01-04", "streams": 50}, {"chart_date": "2024-01-01", "streams": 100}]
    timestamps, streams = history_points(rows, 1)
    assert timestamps == [observation_timestamp("2024-01-01"), observation_timestamp("2024-01-02"), observation_timestamp("2024-01-04")]
    assert streams[0] == 100 and math.isnan(streams[1]) and streams[2] == 50
    panel = ChartPanel("TEST DATA")
    render_history(panel, rows, "daily")
    assert panel.plot.viewRange()[1][0] == 0
    assert panel.plot.getAxis("bottom")._tickLevels[0] == [
        (observation_timestamp("2024-01-01"), "2024-01-01"),
        (observation_timestamp("2024-01-04"), "2024-01-04"),
    ]
    monkeypatch.setattr(MainWindow, "refresh_dashboard", lambda self: None)
    window = MainWindow(database)
    try:
        for rows, refresh, table, control in [
            (database.get_top_tracks(), window.refresh_songs_table, window.songs_table, window.song_hide_repeats),
            (database.get_artist_summary(), window.refresh_artists_table, window.artist_table, window.artist_hide_repeats),
            (database.get_album_rankings(), window.refresh_albums_table, window.album_table, window.album_hide_repeats),
        ]:
            refresh(rows)
            before = [[table.item(index, column).text() for column in range(table.columnCount())] for index in range(table.rowCount())]
            assert any("Repeat" in value for row in before for value in row)
            control.setChecked(True)
            control.setChecked(False)
            after = [[table.item(index, column).text() for column in range(table.columnCount())] for index in range(table.rowCount())]
            assert before == after
        assert window.chart_type_combo.findData("weekly_derived") >= 0
        assert window.weekly_import_button.isEnabled()
    finally:
        panel.close()
        window.close()
        app.processEvents()
