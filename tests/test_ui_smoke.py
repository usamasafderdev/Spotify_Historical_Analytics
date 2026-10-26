from __future__ import annotations

import os
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QEventLoop, QTimer, Qt
from PySide6.QtWidgets import QApplication, QHeaderView, QScrollArea

from spotify_historical_analytics.db import DatabaseManager
from spotify_historical_analytics.importer import import_csv_file
from spotify_historical_analytics.ui.main_window import MainWindow


FIXTURE_CSV = Path(__file__).parent / "fixtures" / "synthetic_us_daily.csv"


def wait_for_dashboard(window: MainWindow) -> None:
    timeout = QTimer()
    timeout.setSingleShot(True)
    loop = QEventLoop()
    timeout.timeout.connect(loop.quit)
    window.dashboard_updated.connect(loop.quit)
    if not window._has_current_dashboard_payload():
        timeout.start(10_000)
        loop.exec()
    window.dashboard_updated.disconnect(loop.quit)
    assert window._has_current_dashboard_payload()


def wait_for_new_dashboard(window: MainWindow, old_generation: int) -> None:
    if window._dashboard_generation > old_generation and window._has_current_dashboard_payload():
        return
    loop = QEventLoop()
    timeout = QTimer()
    timeout.setSingleShot(True)
    timeout.timeout.connect(loop.quit)
    window.dashboard_updated.connect(loop.quit)
    timeout.start(10_000)
    loop.exec()
    window.dashboard_updated.disconnect(loop.quit)
    assert window._dashboard_generation > old_generation
    assert window._has_current_dashboard_payload()


def _assert_detail_dialog(
    app: QApplication,
    show_detail: Callable[[], None],
    expected_title: str,
) -> None:
    titles: list[str] = []

    def close_dialog() -> None:
        dialog = app.activeModalWidget()
        if dialog is None:
            QTimer.singleShot(20, close_dialog)
            return
        titles.append(dialog.windowTitle())
        dialog.accept()

    QTimer.singleShot(0, close_dialog)
    show_detail()
    assert titles and titles[0].startswith(expected_title)


def test_dashboard_navigation_filters_and_database_widgets(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    db = DatabaseManager(tmp_path / "dashboard.db")
    import_csv_file(db, FIXTURE_CSV, "UI Smoke Source", "Local fixture", chart_type="daily", country="US")
    window = MainWindow(db=db)
    assert window.windowTitle() == "US Music Charts Analytics"
    assert not window.windowIcon().isNull()
    window.show()
    wait_for_dashboard(window)

    assert window.pages.count() == 6
    assert window.kpis[0].value.text() == "49,500"
    assert window.songs_table.rowCount() == 2
    assert len(window.streams_chart.plot.listDataItems()) == 1
    snapshot_path = tmp_path / "phase4-dashboard-offscreen.png"
    assert window.grab().save(str(snapshot_path))
    assert snapshot_path.exists()
    original_rows = window.songs_table.rowCount()
    window._on_dashboard_queries_completed(
        {"generation": window._dashboard_generation - 1}
    )
    assert window.songs_table.rowCount() == original_rows

    old_generation = window._dashboard_generation
    window.song_search.setText("song b")
    wait_for_new_dashboard(window, old_generation)
    assert window.songs_table.rowCount() == 1
    assert window.songs_table.item(0, 1).text() == "Song B"

    window.song_search.clear()
    old_generation = window._dashboard_generation
    wait_for_new_dashboard(window, old_generation)
    window.songs_table.sortItems(3, Qt.DescendingOrder)
    assert window.songs_table.item(0, 1).text() == "Song A"

    window.start_edit.setDate(window.start_edit.date().fromString("2024-01-01", "yyyy-MM-dd"))
    window.end_edit.setDate(window.end_edit.date().fromString("2024-01-01", "yyyy-MM-dd"))
    window.apply_filters()
    wait_for_dashboard(window)
    assert window.kpis[0].value.text() == "19,000"

    window.navigate(4)
    app.processEvents()
    assert window.pages.currentIndex() == 4
    assert window.source_table.rowCount() == 1
    assert window.source_table.columnCount() == 13
    assert window.source_table.item(0, 10).text() == "UNVERIFIED"
    assert window.source_table.item(0, 11).text() == "IMPORTED"
    assert window.source_table.verticalHeader().isHidden()
    assert (
        window.source_table.horizontalHeader().sectionResizeMode(0)
        == QHeaderView.ResizeToContents
    )
    assert window.year_table.rowCount() == 20
    window.close()
    db.close()


def test_empty_date_defaults_presets_theme_and_filter_persistence(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    db = DatabaseManager(tmp_path / "empty-date.db")
    window = MainWindow(db=db)
    window.show()
    wait_for_dashboard(window)

    assert window.start_edit.date().toPython().isoformat() == "2017-01-01"
    assert window.end_edit.date().toPython() == date.today()
    assert window.start_edit.maximumDate().toPython() == date.today()
    window.navigate(4)
    app.processEvents()
    assert window.year_table.rowCount() == 20
    assert "RESEARCH ONLY" in window.coverage_summary.text()
    assert window.source_table.rowCount() == 0
    stylesheet = window.styleSheet()
    assert "QLabel { background:transparent;" in stylesheet
    assert "QFrame#card" in stylesheet
    assert "QTableCornerButton::section" in stylesheet

    for days in (7, 30, 90, 365):
        window.preset_combo.setCurrentIndex(window.preset_combo.findData(days))
        assert window.active_end == date.today().isoformat()
        assert window.active_start == (
            date.today() - timedelta(days=days - 1)
        ).isoformat()
    selected_start = window.active_start
    selected_end = window.active_end
    window.navigate(3)
    window.navigate(0)
    assert window.active_start == selected_start
    assert window.active_end == selected_end
    window.reset_filters()
    wait_for_dashboard(window)
    assert window.active_start is None
    assert window.active_end is None
    assert window.start_edit.date().toPython().isoformat() == "2017-01-01"

    for width, height in ((1366, 768), (1600, 900), (1920, 1080)):
        window.resize(width, height)
        app.processEvents()
        assert window.width() == width
        assert window.height() == height
        scroll = window.findChild(QScrollArea, "contentScroll")
        assert scroll is not None
        assert window.pages.width() <= scroll.viewport().width()
        assert scroll.horizontalScrollBar().maximum() == 0
    window.close()


def test_date_defaults_follow_actual_imported_bounds(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    db = DatabaseManager(tmp_path / "actual-bounds.db")
    import_csv_file(db, FIXTURE_CSV, "UI Smoke Source", "Local fixture", chart_type="daily")
    window = MainWindow(db=db)
    window.show()
    wait_for_dashboard(window)
    assert window.start_edit.date().toPython().isoformat() == "2024-01-01"
    assert window.end_edit.date().toPython().isoformat() == "2024-01-04"
    window.close()
    db.close()


def test_pre_2017_imported_date_is_used_as_default(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    db = DatabaseManager(tmp_path / "pre-2017.db")
    db.register_chart_record(
        batch_id="pre-2017-fixture",
        source="Authorized historical fixture",
        source_license="Test fixture only",
        chart_type="daily",
        country="US",
        chart_date="2016-12-31",
        weekly_start=None,
        weekly_end=None,
        position=1,
        track_id="pre-2017-track",
        track_name="Historical Test Song",
        artist_names="Test Artist",
        streams=100,
        original_url=None,
    )
    window = MainWindow(db=db)
    window.show()
    wait_for_dashboard(window)
    assert window.start_edit.date().toPython().isoformat() == "2016-12-31"
    assert "before the client default reporting window of 2017" in window.start_edit.toolTip()
    window.close()
    db.close()


def test_demo_mode_uses_separate_database_and_returns_to_production(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    db = DatabaseManager(tmp_path / "production.db")
    import_csv_file(db, FIXTURE_CSV, "Real fixture", "Fixture license")
    production_total = db.get_summary(chart_type="daily")["total_streams"]
    window = MainWindow(db=db)
    window.show()
    wait_for_dashboard(window)

    old_generation = window._dashboard_generation
    window.load_demo_data()
    wait_for_new_dashboard(window, old_generation)
    assert window._demo_mode
    assert window.db.db_path != db.db_path
    assert window.demo_banner.isVisible()
    assert window.songs_table.rowCount() > 0
    window.navigate(2)
    assert window.artist_table.rowCount() == 4
    window.navigate(3)
    assert window.album_table.rowCount() == 4
    assert window.album_table.item(0, 3).text().replace(",", "").isdigit()
    assert window._demo_db is not None
    assert window._demo_db.get_available_date_bounds(
        include_demo=True, chart_type="weekly"
    )["earliest"] == "2017-01-02"
    assert db.get_summary(chart_type="daily")["total_streams"] == production_total

    song_key = str(window.songs_table.item(0, 1).data(Qt.UserRole))
    song_detail = window.db.get_song_detail(
        "", "", include_demo=True, chart_type="daily", track_key=song_key
    )
    assert song_detail is not None
    song_history = window.db.get_streams_over_time(
        chart_type="daily", track_key=song_key, include_demo=True
    )
    _assert_detail_dialog(
        app,
        lambda: window._show_song_detail(song_detail, song_history),
        "Song details",
    )

    artist_key = str(window.artist_table.item(0, 1).data(Qt.UserRole))
    artist_detail = window.db.get_artist_detail(
        artist_key, chart_type="daily", include_demo=True
    )
    assert artist_detail is not None
    artist_history = window.db.get_artist_streams_over_time(
        artist_key, chart_type="daily", include_demo=True
    )
    _assert_detail_dialog(
        app,
        lambda: window._show_artist_detail(artist_detail, artist_history),
        "Artist details",
    )

    album_id = str(window.album_table.item(0, 1).data(Qt.UserRole))
    album_detail = window.db.get_album_detail(
        album_id, chart_type="daily", include_demo=True
    )
    assert album_detail is not None
    album_tracks = window.db.get_album_tracks(
        album_id, chart_type="daily", include_demo=True
    )
    album_history = window.db.get_album_streams_over_time(
        album_id, chart_type="daily", include_demo=True
    )
    _assert_detail_dialog(
        app,
        lambda: window._show_album_detail(album_detail, album_tracks, album_history),
        "Album details",
    )

    old_generation = window._dashboard_generation
    window.load_demo_data()
    wait_for_new_dashboard(window, old_generation)
    assert not window._demo_mode
    assert window.db is db
    assert db.get_summary(chart_type="daily")["total_streams"] == production_total
    window.close()
    db.close()


def test_first_run_empty_state_and_demo_preview_widgets(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    db = DatabaseManager(tmp_path / "empty-production.db")
    window = MainWindow(db=db)
    window.show()
    wait_for_dashboard(window)

    assert window._demo_mode is False
    assert window.active_chart_type == "daily"
    assert window.active_start is None
    assert window.active_end is None
    assert window.start_edit.date().toPython().isoformat() == "2017-01-01"
    assert window.end_edit.date().toPython() == date.today()
    assert window.overview_empty.text() == "No historical chart data is loaded yet."
    assert window.overview_empty.isVisible()
    assert window.overview_empty_actions.isVisible()
    assert window.empty_import_button.text() == "Import Authorized Dataset"
    assert window.empty_demo_button.text() == "Preview Demo Dashboard"
    assert window.empty_sources_button.text() == "View Data Sources"
    assert not window.overview_data.isVisible()
    assert all(widget.value.text() == "—" for widget in window.kpis)

    window.empty_sources_button.click()
    assert window.pages.currentIndex() == 4
    window.navigate(0)

    old_generation = window._dashboard_generation
    window.empty_demo_button.click()
    wait_for_new_dashboard(window, old_generation)
    assert window._demo_mode
    assert window.demo_banner.isVisible()
    assert "DEMO / SYNTHETIC DATA" in window.demo_banner.text()
    assert window.overview_data.isVisible()
    assert not window.overview_empty.isVisible()
    assert int(window.kpis[0].value.text().replace(",", "")) > 0
    assert window.songs_table.rowCount() > 0
    assert window.artist_table.rowCount() > 0
    assert window.album_table.rowCount() > 0
    assert window.streams_chart.plot.listDataItems()
    assert window.top_songs_chart.plot.listDataItems()

    old_generation = window._dashboard_generation
    window.chart_type_combo.setCurrentIndex(window.chart_type_combo.findData("weekly"))
    wait_for_new_dashboard(window, old_generation)
    assert window.active_chart_type == "weekly"
    assert window.songs_table.rowCount() > 0
    assert window.artist_table.rowCount() > 0
    assert window.album_table.rowCount() > 0

    old_generation = window._dashboard_generation
    window.load_demo_data()
    wait_for_new_dashboard(window, old_generation)
    assert not window._demo_mode
    assert not window.demo_banner.isVisible()
    assert window.db is db
    assert db.connection.execute("SELECT COUNT(*) FROM chart_records").fetchone()[0] == 0
    assert window.overview_empty.isVisible()
    assert not window.overview_data.isVisible()

    window.close()
    db.close()
