from __future__ import annotations

import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QEventLoop, QThread, Qt, QTimer
from PySide6.QtWidgets import QApplication

from spotify_historical_analytics.db import DatabaseManager
from spotify_historical_analytics.ui.workers import ImportWorker


FIXTURE_CSV = Path(__file__).parent / "fixtures" / "synthetic_us_daily.csv"


def test_chart_import_worker_uses_independent_database_connection(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    database_path = tmp_path / "worker.db"
    main_connection = DatabaseManager(database_path)
    worker = ImportWorker(
        db_path=str(database_path),
        kind="chart",
        file_path=str(FIXTURE_CSV),
        source_name="Background fixture",
        source_license="Synthetic test fixture",
        chart_type="daily",
    )
    thread = QThread()
    worker.moveToThread(thread)
    event_loop = QEventLoop()
    result_objects: list[object] = []
    failures: list[str] = []
    worker.completed.connect(result_objects.append)
    worker.failed.connect(failures.append)
    worker.completed.connect(thread.quit, Qt.DirectConnection)
    worker.failed.connect(thread.quit, Qt.DirectConnection)
    thread.started.connect(worker.run)
    thread.finished.connect(event_loop.quit)
    thread.finished.connect(worker.deleteLater)
    thread.start()
    QTimer.singleShot(10_000, event_loop.quit)
    event_loop.exec()
    thread.wait()

    assert not failures
    assert result_objects
    assert result_objects[0].valid_rows == 5
    assert main_connection.get_summary(chart_type="daily")["total_streams"] == 49500
    main_connection.close()
