import os
import time

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest
from PySide6.QtCore import QThread, Qt
from PySide6.QtWidgets import QApplication

from spotify_historical_analytics.db import DatabaseManager
from spotify_historical_analytics.ui.import_dialog import ImportDialog
from spotify_historical_analytics.ui.workers import DashboardQueryWorker


def wait(app, predicate):
    deadline = time.monotonic() + 10
    while not predicate() and time.monotonic() < deadline:
        app.processEvents()
        time.sleep(0.005)
    assert predicate()


@pytest.mark.parametrize("filename,data,message", [
    ("bad.csv.gz", b"This is not gzip", "compressed CSV"),
    ("bad.xlsx", b"This is not XLSX", "Excel workbook"),
    ("bad.csv", b"\xff\x00", "UTF-8"),
])
def test_corrupt_imports_have_actionable_errors_without_production_writes(tmp_path, filename, data, message):
    app = QApplication.instance() or QApplication([])
    source = tmp_path / filename
    source.write_bytes(data)
    dialog = ImportDialog(tmp_path / "production.db", tmp_path / "staging.db")
    dialog.select_file(source)
    wait(app, lambda: dialog._thread is None)
    assert message in dialog.warnings.text()
    assert "Traceback" not in dialog.warnings.text()
    assert not dialog.import_button.isEnabled()
    assert not (tmp_path / "production.db").exists()
    dialog.close()


def test_superseded_dashboard_query_interrupts_sqlite_without_failure(tmp_path, monkeypatch):
    import threading
    app = QApplication.instance() or QApplication([])
    entered = threading.Event()
    def slow_summary(db, **filters):
        entered.set()
        db.connection.execute("WITH RECURSIVE n(x) AS (VALUES(1) UNION ALL SELECT x+1 FROM n WHERE x<100000000) SELECT SUM(x) FROM n").fetchone()
        raise AssertionError("Cancellation should have interrupted this query")
    monkeypatch.setattr(DatabaseManager, "get_summary", slow_summary)
    worker = DashboardQueryWorker(str(tmp_path / "queries.db"), 1, None, None, "daily", "", "", "", 50, 50, 50)
    thread = QThread()
    worker.moveToThread(thread)
    cancelled, failures = [], []
    worker.cancelled.connect(lambda: cancelled.append(True))
    worker.failed.connect(failures.append)
    worker.cancelled.connect(thread.quit, Qt.DirectConnection)
    thread.started.connect(worker.run)
    thread.start()
    try:
        wait(app, entered.is_set)
        worker.cancel()
        wait(app, lambda: not thread.isRunning())
        app.processEvents()
        assert cancelled and not failures
    finally:
        worker.cancel()
        thread.quit()
        thread.wait()


def test_demo_smoke_closes_database_before_temporary_directory_cleanup(tmp_path):
    import subprocess
    import sys
    temporary = tmp_path / "temp"
    temporary.mkdir()
    environment = os.environ.copy()
    environment.update(QT_QPA_PLATFORM="offscreen", SPOTIFY_ANALYTICS_DATA_DIR=str(tmp_path / "userdata"), TEMP=str(temporary), TMP=str(temporary))
    result = subprocess.run([sys.executable, "-m", "spotify_historical_analytics", "--demo-smoke-test"], env=environment, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    log = (tmp_path / "userdata/logs/application.log").read_text(encoding="utf-8")
    assert "Demo UI smoke test passed" in log
    assert " ERROR " not in log and " CRITICAL " not in log
    assert not list(temporary.glob("spotify-analytics-demo-*"))
