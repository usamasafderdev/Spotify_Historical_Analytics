from __future__ import annotations

import gzip
import os
from pathlib import Path
import threading
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest
from openpyxl import Workbook
from PySide6.QtWidgets import QApplication, QWizard

from spotify_historical_analytics.db import DatabaseManager
from spotify_historical_analytics.import_sessions import ImportSessionStore
from spotify_historical_analytics.ui.import_dialog import ImportDialog
from spotify_historical_analytics.ui.main_window import MainWindow


STANDARD = (
    "Date,Track,Artist,Streams,Region,Chart,Track ID\n"
    "2024-01-01,Synthetic Song,Synthetic Artist,1234,US,daily,track-1\n"
    "2024-01-01,Synthetic Song,Synthetic Artist,1234,US,daily,track-1\n"
    "invalid,Bad Date,Synthetic Artist,1234,US,daily,track-2\n"
    "2024-01-02,Other Market,Synthetic Artist,2000,CA,daily,track-3\n"
)


def wait_until(app, predicate):
    deadline = time.monotonic() + 15
    while not predicate() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    assert predicate(), "Background operation timed out"


@pytest.fixture
def app():
    return QApplication.instance() or QApplication([])


@pytest.mark.parametrize("suffix", [".csv", ".csv.gz", ".xlsx"])
def test_dialog_browse_preview_import_duplicates_and_backup(app, tmp_path, monkeypatch, suffix):
    source = tmp_path / f"synthetic{suffix}"
    if suffix == ".csv.gz":
        with gzip.open(source, "wt", encoding="utf-8") as stream:
            stream.write(STANDARD)
    elif suffix == ".xlsx":
        workbook = Workbook()
        for line in STANDARD.splitlines():
            workbook.active.append(line.split(","))
        workbook.save(source)
    else:
        source.write_text(STANDARD)
    production = tmp_path / "production.db"
    DatabaseManager(production).close()
    dialog = ImportDialog(production, tmp_path / "staging.db")
    dialog.show()
    monkeypatch.setattr("spotify_historical_analytics.ui.import_dialog.QFileDialog.getOpenFileName", lambda *a: (str(source), ""))
    dialog.browse_button.click()
    wait_until(app, lambda: dialog._thread is None)
    assert not isinstance(dialog, QWizard)
    assert dialog._summary.processed_rows == 4
    assert dialog._summary.accepted_rows == 2
    assert dialog._summary.rejected_rows == 2
    assert "2024-01-01" in dialog.coverage_label.text()
    assert "invalid_date" in dialog.warnings.text()
    assert dialog.import_button.isEnabled()
    assert not any("manifest" in widget.text().lower() for widget in dialog.findChildren(type(dialog.status)))
    dialog.import_button.click()
    wait_until(app, lambda: dialog._thread is None)
    assert dialog.result["imported_rows"] == 1
    assert dialog.result["duplicates_skipped"] == 1
    assert "Rejected invalid records: 2" in dialog.result_label.text()
    assert Path(dialog.result["backup_path"]).is_file()
    database = DatabaseManager(production)
    assert database.connection.execute("select count(*) from chart_records").fetchone()[0] == 1
    assert database.connection.execute("pragma integrity_check").fetchone()[0] == "ok"
    assert database.connection.execute("select count(*) from import_rights_approvals").fetchone()[0] == 0
    assert "User-selected local" in database.connection.execute("select remarks from sources").fetchone()[0]
    database.close()
    dialog.close()


@pytest.mark.parametrize("adapter", ["MGD+", "Dhruvil Spotify Charts"])
def test_known_schemas_auto_detect_and_never_require_mapping(app, tmp_path, adapter):
    source = tmp_path / "known.csv"
    if adapter == "MGD+":
        source.write_text("ID\tTrack\tArtist\tPosition\tStreams\tTrend\tDate\tChart\tmarket\n"
                          "stable-id\tSynthetic\tArtist\t1\t100\tNEW\t2024-01-01\ttop200\tUS\n"
                          "bad-rank\tInvalid rank\tArtist\t0\t100\tNEW\t2024-01-01\ttop200\tUS\n")
    else:
        source.write_text("title,rank,date,artist,url,region,chart,trend,streams\n"
                          "Synthetic,1,2024-01-01,Artist,https://open.spotify.com/track/0123456789ABCDEFGHIJKL,us,top200,NEW,100\n"
                          "Viral,1,2024-01-01,Artist,https://open.spotify.com/track/0123456789ABCDEFGHIJKL,us,viral,NEW,999\n"
                          "Bad rank,0,2024-01-01,Artist,https://open.spotify.com/track/0123456789ABCDEFGHIJKL,us,top200,NEW,100\n")
    dialog = ImportDialog(tmp_path / "production.db", tmp_path / "staging.db")
    dialog.show()
    dialog.select_file(source)
    wait_until(app, lambda: dialog._thread is None)
    assert dialog._inspection["adapter"] == adapter
    assert dialog._summary.accepted_rows == 1
    assert dialog.import_button.isEnabled()
    assert not dialog.mapping_section.isVisible()
    assert dialog._summary.rejection_counts.get("invalid_chart_position") == 1
    if adapter != "MGD+":
        assert dialog._summary.rejection_counts.get("streamless_viral_chart") == 1
    dialog.close()


def test_unknown_schema_can_be_mapped_in_same_dialog(app, tmp_path):
    source = tmp_path / "unknown.csv"
    source.write_text("when,what,who,amount,where\n2024-01-01,Synthetic,Artist,100,US\n")
    dialog = ImportDialog(tmp_path / "production.db", tmp_path / "staging.db")
    dialog.show()
    dialog.select_file(source)
    wait_until(app, lambda: dialog._thread is None)
    assert dialog.mapping_toggle.isChecked()
    assert not dialog.import_button.isEnabled()
    for name, column in dict(date="when", track_name="what", artist_names="who", streams="amount", country="where").items():
        combo = dialog.mapping_combos[name]
        combo.setCurrentIndex(combo.findData(column))
    dialog.validate_button.click()
    wait_until(app, lambda: dialog._thread is None)
    assert dialog._summary.accepted_rows == 1
    assert dialog.import_button.isEnabled()
    dialog.close()


def test_invalid_file_error_and_cancelled_browse_preserve_database(app, tmp_path, monkeypatch):
    dialog = ImportDialog(tmp_path / "production.db", tmp_path / "staging.db")
    dialog.show()
    monkeypatch.setattr("spotify_historical_analytics.ui.import_dialog.QFileDialog.getOpenFileName", lambda *a: ("", ""))
    dialog.browse_button.click()
    assert dialog._thread is None
    dialog.select_file(tmp_path / "missing.csv")
    wait_until(app, lambda: dialog._thread is None)
    assert "does not exist" in dialog.warnings.text()
    assert dialog.format_label.text() == "Unavailable"
    assert not dialog.import_button.isEnabled()
    assert not (tmp_path / "production.db").exists()
    dialog.cancel_button.click()
    assert not dialog.isVisible()


def test_cancel_running_validation_waits_for_worker_without_production_writes(app, tmp_path, monkeypatch):
    source = tmp_path / "synthetic.csv"
    source.write_text(STANDARD)
    entered = threading.Event()
    original = ImportSessionStore.prepare

    def prepare(store, session, cancel, progress, schema):
        entered.set()
        assert cancel.wait(5)
        return original(store, session, cancel, progress, schema)

    monkeypatch.setattr(ImportSessionStore, "prepare", prepare)
    dialog = ImportDialog(tmp_path / "production.db", tmp_path / "staging.db")
    dialog.show()
    dialog.select_file(source)
    wait_until(app, entered.is_set)
    dialog.cancel_button.click()
    assert dialog._cancel.is_set()
    wait_until(app, lambda: dialog._thread is None)
    assert not dialog.isVisible()
    assert not (tmp_path / "production.db").exists()


def test_main_window_uses_single_import_dialog_and_refreshes(app, tmp_path, monkeypatch):
    database = DatabaseManager(tmp_path / "database" / "analytics.db")
    window = MainWindow(db=database)
    window.show()
    wait_until(app, window._has_current_dashboard_payload)
    opened = []
    monkeypatch.setattr(ImportDialog, "exec", lambda self: opened.append(self))
    window.import_button.click()
    assert len(opened) == 1
    assert opened[0].windowTitle() == "Import Historical Music Data"
    assert window.import_button.text() == "Import Dataset"
    window.navigate(5)
    window.import_page_button.click()
    assert len(opened) == 2
    assert not hasattr(window, "_offer_resume_import")
    window.close()
    database.close()


def test_explicit_weekly_detection_and_daily_separation(app, tmp_path):
    source = tmp_path / "weekly.csv"
    source.write_text("Date,Track,Artist,Streams,Region,Chart,Track ID,week_start,week_end\n"
                      "2024-01-07,Synthetic,Artist,1000,US,weekly,track-1,2024-01-01,2024-01-07\n")
    dialog = ImportDialog(tmp_path / "production.db", tmp_path / "staging.db")
    dialog.show()
    dialog.select_file(source)
    wait_until(app, lambda: dialog._thread is None)
    assert dialog.cadence_combo.currentData() == "weekly"
    assert dialog._summary.accepted_rows == 1
    dialog.import_button.click()
    wait_until(app, lambda: dialog._thread is None)
    database = DatabaseManager(tmp_path / "production.db")
    assert database.get_summary(chart_type="weekly")["total_streams"] == 1000
    assert database.get_summary(chart_type="daily")["total_streams"] == 0
    database.close()
    dialog.close()
