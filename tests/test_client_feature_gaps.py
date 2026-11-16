from __future__ import annotations

import csv
from datetime import date, timedelta
import gzip
import os

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest
from openpyxl import Workbook
from PySide6.QtWidgets import QApplication

from spotify_historical_analytics.db import DatabaseManager
from spotify_historical_analytics.import_sessions import ImportSessionStore
from spotify_historical_analytics.services.appearances import chart_showings
from spotify_historical_analytics.ui.appearance_dialog import AppearanceDialog
from spotify_historical_analytics.ui.import_dialog import ImportTask
from spotify_historical_analytics.weekly_import import import_weekly_files


@pytest.fixture
def showings_db(tmp_path):
    db = DatabaseManager(tmp_path / "TEST-DATA.db")
    for index in range(4):
        track_id = str(index + 1).zfill(22)
        artist_id = str(index + 11).zfill(22)
        album_id = str(index + 21).zfill(22)
        db.connection.execute("INSERT INTO artists(artist_id, artist_name) VALUES (?, 'TEST DATA same name')", (artist_id,))
        db.connection.execute("INSERT INTO albums(album_id, album_name) VALUES (?, 'TEST DATA same name')", (album_id,))
        db.connection.execute("INSERT INTO track_artists(track_id, artist_id, mapping_status) VALUES (?, ?, 'id_match')", (track_id, artist_id))
        db.connection.execute("INSERT INTO track_albums(track_id, album_id, mapping_status) VALUES (?, ?, 'id_match')", (track_id, album_id))
        for day in range(60 if index == 0 else 1):
            db.connection.execute(
                """INSERT INTO chart_records(batch_id, source, chart_type, country, chart_date,
                    position, track_id, track_name, artist_names, streams)
                    VALUES ('TEST DATA', 'TEST DATA', 'daily', 'US', ?, ?, ?, 'TEST DATA same name', 'TEST DATA credit', ?)""",
                ((date(2024, 1, 1) + timedelta(days=day)).isoformat(),
                 60 - day if index == 0 else 61 + index, track_id, 1000 - day if index == 0 else 100),
            )
    db.connection.execute(
        """INSERT INTO chart_records(batch_id, source, chart_type, country, chart_date,
            position, track_id, track_name, artist_names, streams)
            SELECT batch_id, 'TEST DATA duplicate', chart_type, country, chart_date,
                position, track_id, track_name, artist_names, streams FROM chart_records LIMIT 1"""
    )
    db.connection.commit()
    yield db
    db.close()


@pytest.mark.parametrize("category", ["songs", "artists", "albums"])
def test_counts_and_top_n_use_all_eligible_showings(showings_db, category):
    visible = chart_showings(showings_db, category, limit=50)
    assert len(visible) == 50
    assert len({row["entity_id"] for row in visible}) == 1
    assert {row["chart_appearances"] for row in visible} == {60}
    hidden = chart_showings(showings_db, category, limit=50, hide_repeats=True)
    assert len(hidden) == len({row["entity_id"] for row in hidden}) == 4
    assert sorted(row["chart_appearances"] for row in hidden) == [1, 1, 1, 60]
    assert len(chart_showings(showings_db, category, limit=3, hide_repeats=True)) == 3
    assert showings_db.get_summary()["total_streams"] == sum(1000 - day for day in range(60)) + 300


@pytest.mark.parametrize("category", ["songs", "artists", "albums"])
@pytest.mark.parametrize("sort,expected_date", [("streams", "2024-01-01"), ("position", "2024-02-29"),
                                                 ("newest", "2024-02-29"), ("oldest", "2024-01-01")])
def test_sort_selects_representative_before_limit(showings_db, category, sort, expected_date):
    rows = chart_showings(showings_db, category, hide_repeats=True, sort=sort, limit=4)
    assert next(row for row in rows if row["chart_appearances"] > 1)["chart_date"] == expected_date


@pytest.mark.parametrize("category", ["songs", "artists", "albums"])
def test_date_search_and_source_filter_before_repeat_count(showings_db, category):
    rows = chart_showings(showings_db, category, start_date="2024-02-01", end_date="2024-02-10",
                          search="same name", limit=1, hide_repeats=True)
    assert len(rows) == 1 and rows[0]["chart_appearances"] == 10
    assert chart_showings(showings_db, category, chart_type="weekly") == []
    assert chart_showings(showings_db, category, search="absent") == []


def test_visible_hide_repeats_dialog(showings_db):
    app = QApplication.instance() or QApplication([])
    before = showings_db.get_top_tracks()
    dialog = AppearanceDialog(showings_db, "songs", {"chart_type": "daily"}, "", 50)
    try:
        assert dialog.table.rowCount() == 50
        dialog.hide_repeats.setChecked(True)
        assert dialog.table.rowCount() == 4
        assert "Repeat (60)" in [dialog.table.item(index, 5).text() for index in range(4)]
        dialog.sort.setCurrentIndex(dialog.sort.findData("position"))
        assert next(row for row in dialog.rows if row["chart_appearances"] == 60)["chart_date"] == "2024-02-29"
        dialog.hide_repeats.setChecked(False)
        assert dialog.table.rowCount() == 50
        assert showings_db.get_top_tracks() == before
    finally:
        dialog.close()
        app.processEvents()


def test_artist_multiple_tracks_on_one_date_are_one_showing(showings_db):
    showings_db.connection.execute(
        "INSERT INTO track_artists(track_id, artist_id, mapping_status) VALUES (?, ?, 'id_match')",
        (str(2).zfill(22), str(11).zfill(22)),
    )
    showings_db.connection.commit()
    rows = chart_showings(showings_db, "artists", hide_repeats=True, limit=4)
    artist = next(row for row in rows if row["entity_id"] == str(11).zfill(22))
    assert artist["chart_appearances"] == 60
    assert artist["streams"] == 1100


def write_original(path, modern=False, streams=123, extra=None):
    headers = ["rank", "uri", "artist_names", "track_name", "streams"] if modern else ["Position", "Track Name", "Artist", "Streams", "URL"]
    values = [1, "spotify:track:" + "A" * 22, "TEST DATA artist", "TEST DATA song", streams] if modern else [1, "TEST DATA song", "TEST DATA artist", streams, "https://open.spotify.com/track/" + "A" * 22]
    if extra:
        headers.extend(extra)
        values.extend(extra.values())
    if path.suffix == ".xlsx":
        book = Workbook()
        book.active.append(headers)
        book.active.append(values)
        book.save(path)
        book.close()
    else:
        opener = gzip.open if path.suffix == ".gz" else open
        with opener(path, "wt", newline="", encoding="utf-8") as handle:
            if not modern:
                handle.write('"Note that these figures are generated using a formula that protects against artificial inflation."\n')
            writer = csv.writer(handle)
            writer.writerow(headers)
            writer.writerow(values)


@pytest.mark.parametrize("suffix", [".csv", ".csv.gz", ".xlsx"])
@pytest.mark.parametrize("modern,period", [(True, "2024-02-08"), (False, "2024-02-02--2024-02-09"),
                                          (False, "2024-02-02--2024-02-08"), (False, "2024-02-01--2024-02-08")])
def test_original_weekly_formats_without_custom_columns(tmp_path, suffix, modern, period):
    path = tmp_path / ("regional-us-weekly-" + period + suffix)
    write_original(path, modern)
    db = DatabaseManager(tmp_path / "production.db")
    try:
        results = import_weekly_files(db, [path, path])
        assert [row.get("imported_rows") for row in results] == [1, 0], results
        row = db.connection.execute("SELECT * FROM chart_records").fetchone()
        assert (row["weekly_start"], row["weekly_end"], row["chart_date"]) == ("2024-02-02", "2024-02-08", "2024-02-08")
        assert db.get_summary()["total_streams"] == 0
        assert db.get_summary(chart_type="weekly")["total_streams"] == 123
        write_original(path, modern, streams=456)
        assert "conflict" in import_weekly_files(db, [path])[0]["error"].lower()
        assert db.get_summary(chart_type="weekly")["total_streams"] == 123
    finally:
        db.close()


@pytest.mark.parametrize("filename,extra", [
    ("regional-us-weekly-2024-02-09.csv", None),
    ("regional-us-weekly-2024-02-03--2024-02-10.csv", None),
    ("regional-ca-weekly-2024-02-08.csv", None),
    ("renamed-weekly.csv", None),
    ("regional-us-weekly-2024-02-08.csv", {"Region": "CA"}),
    ("regional-us-weekly-2024-02-08.csv", {"Weekly Start": "2024-02-01", "Weekly End": "2024-02-07"}),
])
def test_ambiguous_or_conflicting_weekly_context_rejects(tmp_path, filename, extra):
    path = tmp_path / filename
    write_original(path, extra=extra)
    db = DatabaseManager(tmp_path / "production.db")
    try:
        assert import_weekly_files(db, [path])[0]["status"] == "Failed"
        assert db.connection.execute("SELECT COUNT(*) FROM chart_records").fetchone()[0] == 0
    finally:
        db.close()


def test_original_weekly_autodetection_in_existing_import_task(tmp_path):
    import threading

    path = tmp_path / "regional-us-weekly-2024-02-08.csv"
    write_original(path, modern=True)
    task = ImportTask(tmp_path / "staging.db", tmp_path / "production.db", threading.Event(), "preview",
                      path=str(path), source="TEST DATA", cadence="daily", auto_cadence=True)
    results, failures = [], []
    task.completed.connect(results.append)
    task.failed.connect(failures.append)
    task.run()
    assert not failures
    assert results[0]["inspection"]["cadence"] == "weekly"
    assert results[0]["summary"].accepted_rows == 1


def test_weekly_custom_identifier_and_period_requirements_remain_strict(tmp_path):
    path = tmp_path / "custom.csv"
    path.write_text("date,track_name,artist_names,streams,country,track_id,weekly_start,weekly_end\n2024-02-08,TEST DATA,TEST DATA,123,US,synthetic-track-a,2024-02-02,2024-02-08\n")
    db = DatabaseManager(tmp_path / "production.db")
    try:
        assert "22-character" in import_weekly_files(db, [path])[0]["error"]
    finally:
        db.close()
