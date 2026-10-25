from __future__ import annotations

import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QEventLoop, QThread, Qt, QTimer
from PySide6.QtWidgets import QApplication

from spotify_historical_analytics.db import DatabaseManager
from spotify_historical_analytics.importer import import_csv_file
from spotify_historical_analytics.ui.workers import DetailQueryWorker, ImportWorker


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
    progress_messages: list[str] = []
    worker.completed.connect(result_objects.append)
    worker.failed.connect(failures.append)
    worker.progress.connect(progress_messages.append)
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
    assert any("Reading CSV" in message for message in progress_messages)
    assert any("Validating and importing" in message for message in progress_messages)
    assert "Chart import transaction committed." in progress_messages
    assert main_connection.get_summary(chart_type="daily")["total_streams"] == 49500
    main_connection.close()


def test_song_detail_query_worker_returns_filtered_history(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    database_path = tmp_path / "detail-worker.db"
    main_connection = DatabaseManager(database_path)
    import_csv_file(
        main_connection, FIXTURE_CSV, "Detail fixture", "Synthetic test fixture"
    )
    thread = QThread()
    worker = DetailQueryWorker(
        db_path=str(database_path),
        generation=3,
        kind="songs",
        key="aaa",
        start_date="2024-01-01",
        end_date="2024-01-02",
        chart_type="daily",
        dashboard_generation=7,
    )
    worker.moveToThread(thread)
    event_loop = QEventLoop()
    results: list[object] = []
    failures: list[object] = []
    worker.completed.connect(results.append)
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
    assert results
    result = results[0]
    assert result["generation"] == 3
    assert result["dashboard_generation"] == 7
    assert result["detail"]["total_streams"] == 22000
    assert [row["chart_date"] for row in result["streams"]] == [
        "2024-01-01",
        "2024-01-02",
    ]
    main_connection.close()
