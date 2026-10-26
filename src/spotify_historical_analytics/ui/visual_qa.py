"""Opt-in automation of the real single import dialog with isolated fixtures."""
from __future__ import annotations
import json
import time
from pathlib import Path
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QFileDialog, QLineEdit, QWizard
from ..db import DatabaseManager
from .import_dialog import ImportDialog


def run_visual_qa(output: Path, width: int = 840, height: int = 680) -> int:
    output.mkdir(parents=True, exist_ok=True)
    fixture = output / f"fixture-{time.time_ns()}"
    fixture.mkdir()
    source = fixture / "synthetic.csv"
    source.write_text(
        "Date,Track,Artist,Streams,Region,Chart,Track ID\n"
        "2024-01-01,Synthetic Song,Synthetic Artist,1234,US,daily,track-1\n"
        "2024-01-01,Synthetic Song,Synthetic Artist,1234,US,daily,track-1\n"
        "invalid,Synthetic Invalid,Synthetic Artist,1234,US,daily,track-2\n"
        "2024-01-02,Other Market,Synthetic Artist,100,CA,daily,track-3\n"
    )
    production = fixture / "production.db"
    DatabaseManager(production).close()
    app = QApplication.instance()
    dialog = ImportDialog(production, fixture / "staging.db")
    dialog.resize(width, height)
    dialog.show()
    captures = []

    def wait(condition):
        deadline = time.monotonic() + 30
        while not condition() and time.monotonic() < deadline:
            app.processEvents()
            time.sleep(0.005)
        assert condition(), "Import QA timed out"

    def capture(widget, name):
        app.processEvents()
        pixmap = widget.grab()
        assert pixmap.save(str(output / f"{name}.png"))
        if isinstance(widget, ImportDialog):
            image = pixmap.toImage()
            assert image.pixelColor(image.width() - 20, 10).lightnessF() < 0.2
            assert image.pixelColor(10, image.height() - 10).lightnessF() < 0.2
            assert widget.scroll.horizontalScrollBar().maximum() == 0
        captures.append(f"{name}.png")

    capture(dialog, "01-empty-dialog")
    assert not isinstance(dialog, QWizard)
    dialog.select_file(fixture / "missing.csv")
    wait(lambda: dialog._thread is None)
    assert not dialog.import_button.isEnabled()
    capture(dialog, "02-invalid-file")
    chosen = []

    def choose():
        for widget in app.topLevelWidgets():
            if isinstance(widget, QFileDialog) and widget.isVisible():
                widget.setDirectory(str(source.resolve().parent))
                def finish_selection(widget=widget):
                    widget.findChild(QLineEdit, "fileNameEdit").setText(source.name)
                    capture(widget, "03-browse-files")
                    chosen.append(True)
                    widget.accept()
                QTimer.singleShot(150, finish_selection)
                timeout = QTimer(widget)
                timeout.setSingleShot(True)
                timeout.timeout.connect(widget.reject)
                timeout.start(4000)

    QTimer.singleShot(100, choose)
    dialog.browse_button.click()
    assert chosen
    wait(lambda: dialog._thread is None)
    assert dialog._summary.processed_rows == 4
    assert dialog._summary.accepted_rows == 2
    assert dialog._summary.rejected_rows == 2
    assert dialog._summary.exact_duplicates == 1
    capture(dialog, "04-preview-and-coverage")
    dialog.import_button.click()
    capture(dialog, "05-import-progress")
    wait(lambda: dialog._thread is None)
    assert dialog.result["imported_rows"] == 1
    assert dialog.result["duplicates_skipped"] == 1
    capture(dialog, "06-import-result")
    dialog.scroll.verticalScrollBar().setValue(dialog.scroll.verticalScrollBar().maximum())
    capture(dialog, "07-result-bottom")
    assert Path(dialog.result["backup_path"]).is_file()
    database = DatabaseManager(production)
    assert database.connection.execute("select count(*) from chart_records").fetchone()[0] == 1
    assert database.connection.execute("pragma integrity_check").fetchone()[0] == "ok"
    assert database.connection.execute("select count(*) from import_rights_approvals").fetchone()[0] == 0
    database.close()
    scale = dialog.devicePixelRatioF()
    size = [dialog.width(), dialog.height()]
    dialog.close()

    unknown = fixture / "unknown.csv"
    unknown.write_text("when,what,who,amount,where\n2024-01-02,Synthetic,Artist,100,US\n")
    mapping_dialog = ImportDialog(production, fixture / "staging.db")
    mapping_dialog.resize(width, height)
    mapping_dialog.show()
    mapping_dialog.select_file(unknown)
    wait(lambda: mapping_dialog._thread is None)
    capture(mapping_dialog, "08-optional-mapping")
    for field, header in dict(date="when", track_name="what", artist_names="who", streams="amount", country="where").items():
        combo = mapping_dialog.mapping_combos[field]
        combo.setCurrentIndex(combo.findData(header))
    mapping_dialog.validate_button.click()
    wait(lambda: mapping_dialog._thread is None)
    assert mapping_dialog.import_button.isEnabled()
    capture(mapping_dialog, "09-mapping-validated")
    unknown.write_text(unknown.read_text() + "2024-01-03,Changed,Artist,200,US\n")
    mapping_dialog.import_button.click()
    wait(lambda: mapping_dialog._thread is None)
    assert "changed" in mapping_dialog.warnings.text()
    capture(mapping_dialog, "10-import-error")
    mapping_dialog.close()

    cancel_dialog = ImportDialog(production, fixture / "staging.db")
    cancel_dialog.resize(width, height)
    cancel_dialog.show()
    cancel_dialog.select_file(source)
    cancel_dialog.cancel_button.click()
    wait(lambda: cancel_dialog._thread is None)
    assert not cancel_dialog.isVisible()

    from .main_window import MainWindow
    dashboard_database = DatabaseManager(production)
    window = MainWindow(db=dashboard_database)
    window.resize(max(760, width), max(420, height))
    window.show()
    wait(window._has_current_dashboard_payload)
    for index in range(7):
        window.navigate(index)
        capture(window, f"dashboard-{index + 1:02d}")
    window.close()
    dashboard_database.close()
    (output / "results.json").write_text(json.dumps({
        "platform": app.platformName(), "scale": scale, "size": size,
        "captures": captures, "processed": 4, "valid_usa": 2,
        "rejected": 2, "imported": 1, "duplicates_skipped": 1,
        "integrity": "ok", "cancelled_safely": True,
        "changed_source_blocked": True, "manifest_required": False,
    }, indent=2))
    return 0
