from __future__ import annotations

import csv
import json
from pathlib import Path
import traceback

from PySide6.QtCore import QTimer

from .config import APP_ROOT, APP_VERSION, DB_PATH
from .db import DatabaseManager
from .exports import export_rankings
from .runtime import initialize_release_seed
from .services.appearances import chart_showings
from .weekly_import import import_weekly_files


def verify_persistence(directory: Path) -> int:
    try:
        expected = json.loads((directory / "acceptance.json").read_text(encoding="utf-8"))
        assert expected["status"] == "PASS"
        assert not initialize_release_seed()
        db = DatabaseManager()
        try:
            assert db.connection.execute("SELECT COUNT(*) FROM chart_records WHERE track_id=?", (expected["fixture_id"],)).fetchone()[0] == 1
            assert db.connection.execute("SELECT COUNT(*) FROM chart_records").fetchone()[0] == expected["song_records_after"]
            assert db.connection.execute("PRAGMA quick_check").fetchone()[0] == "ok"
        finally:
            db.close()
        (directory / "persistence.json").write_text(json.dumps({"status": "PASS", "existing_database_preserved": True}), encoding="utf-8")
        return 0
    except Exception:
        (directory / "persistence.json").write_text(json.dumps({"status": "FAIL", "error": traceback.format_exc()}), encoding="utf-8")
        return 1


def start_acceptance(app, window, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    report = {"version": APP_VERSION, "database": str(DB_PATH), "profile": str(APP_ROOT), "checks": []}
    state = {"cadence": "daily", "finished": False}
    timer = QTimer(window)
    timer.setSingleShot(True)

    def finish(code: int, error: str | None = None):
        if state["finished"]:
            return
        state["finished"] = True
        timer.stop()
        report["status"] = "PASS" if code == 0 else "FAIL"
        if error:
            report["error"] = error
        (directory / "acceptance.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        window.close()
        app.exit(code)

    def completed():
        try:
            cadence = state["cadence"]
            payload = window._dashboard_payload
            assert payload["overview"]["summary"]["total_streams"] > 0
            assert window.songs_table.rowCount() > 0
            assert window.streams_chart.plot.listDataItems()
            report["checks"].append(f"{cadence} dashboard and rankings")
            if cadence in {"daily", "weekly"}:
                if cadence == "daily":
                    for page in range(window.pages.count()):
                        window.navigate(page)
                        assert window.pages.currentIndex() == page
                    report["checks"].append("all navigation pages")
                state["cadence"] = "weekly" if cadence == "daily" else "weekly_derived"
                window.chart_type_combo.setCurrentIndex(window.chart_type_combo.findData(state["cadence"]))
                return
            verify_details_and_metrics()
            finish(0)
        except Exception:
            finish(2, traceback.format_exc())

    def verify_details_and_metrics():
        from openpyxl import load_workbook
        from .ui.appearance_dialog import AppearanceDialog
        from .ui.history_chart import observation_timestamp, render_history
        from .ui.main_window import ChartPanel

        db = window.db
        assert Path(DB_PATH).drive.upper() == "D:"
        report["song_records_before"] = db.connection.execute("SELECT COUNT(*) FROM chart_records").fetchone()[0]
        track = db.get_top_tracks(limit=1, chart_type="daily")[0]
        history = db.get_streams_over_time(chart_type="daily", track_key=track["track_key"])
        panel = ChartPanel("Installed song graph")
        render_history(panel, history, "daily")
        assert panel.plot.viewRange()[1][0] == 0
        assert observation_timestamp(history[0]["chart_date"]) in panel.plot.listDataItems()[0].xData
        assert panel.history_hover
        panel.close()
        report["checks"].append("song graph actual dates, gaps, hover and zero baseline")
        for category, source in [("songs", "track_streams"), ("artists", "artist_positions"), ("albums", "album_positions"), ("artists", "listeners")]:
            dialog = AppearanceDialog(db, category, {"chart_type": "daily"}, "", 50, parent=window)
            try:
                dialog.source.setCurrentIndex(dialog.source.findData(source))
                assert dialog.rows
                before = dialog.rows
                dialog.hide_repeats.setChecked(True)
                assert dialog.rows
                assert len({row["entity_id"] for row in dialog.rows}) == len(dialog.rows)
                if source != "track_streams":
                    assert all(row["streams"] is None for row in dialog.rows)
                assert any(row["chart_appearances"] > 1 for row in before)
                report["checks"].append(f"{category}/{source} display, repeats, hide repeats")
            finally:
                dialog.close()
        latest = db.connection.execute("SELECT MAX(chart_date) FROM chart_records WHERE chart_type='daily'").fetchone()[0]
        for suffix in ["csv", "xlsx"]:
            destination = directory / f"genuine-daily-export.{suffix}"
            assert export_rankings(db, "songs", destination, latest, latest, "daily", 50) > 0
            if suffix == "xlsx":
                workbook = load_workbook(destination, read_only=True)
                assert "Rankings" in workbook.sheetnames
                workbook.close()
            else:
                assert destination.read_text(encoding="utf-8-sig")
        report["checks"].append("genuine filtered CSV and XLSX exports")
        fixture_id = "Q" * 22
        assert not db.connection.execute("SELECT 1 FROM chart_records WHERE track_id=?", (fixture_id,)).fetchone()
        fixture = directory / "SYNTHETIC-INSTALLED-QA-ONLY.csv"
        with fixture.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["date", "track_name", "artist_names", "streams", "country", "track_id", "chart_type", "weekly_start", "weekly_end"])
            writer.writerow(["2016-01-07", "SYNTHETIC INSTALLED QA ONLY", "SYNTHETIC QA", 1, "US", fixture_id, "weekly", "2016-01-01", "2016-01-07"])
        result = import_weekly_files(db, [fixture])[0]
        assert result["status"] == "Imported", result
        result = import_weekly_files(db, [fixture])[0]
        assert result["status"] == "Imported", result
        assert db.connection.execute("SELECT COUNT(*) FROM chart_records WHERE track_id=?", (fixture_id,)).fetchone()[0] == 1
        report["fixture_id"] = fixture_id
        report["song_records_after"] = db.connection.execute("SELECT COUNT(*) FROM chart_records").fetchone()[0]
        assert report["song_records_after"] == report["song_records_before"] + 1
        report["checks"].append("tiny isolated weekly import and duplicate protection")

    window.dashboard_updated.connect(completed)
    timer.timeout.connect(lambda: finish(3, "Installed dashboard verification exceeded ten minutes"))
    timer.start(600_000)
    if window._dashboard_payload is not None:
        QTimer.singleShot(0, completed)
