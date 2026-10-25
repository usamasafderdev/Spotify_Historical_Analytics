from __future__ import annotations

import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QEventLoop, QTimer, Qt
from PySide6.QtWidgets import QApplication

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


def test_dashboard_navigation_filters_and_database_widgets(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    db = DatabaseManager(tmp_path / "dashboard.db")
    import_csv_file(db, FIXTURE_CSV, "UI Smoke Source", "Local fixture", chart_type="daily", country="US")
    window = MainWindow(db=db)
    window.show()
    wait_for_dashboard(window)

    assert window.pages.count() == 6
    assert window.kpis[0].value.text() == "49,500"
    assert window.songs_table.rowCount() == 2
    assert len(window.streams_chart.plot.listDataItems()) == 1

    window.song_search.setText("song b")
    assert window.songs_table.rowCount() == 1
    assert window.songs_table.item(0, 1).text() == "Song B"

    window.song_search.clear()
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
    window.close()
    db.close()
