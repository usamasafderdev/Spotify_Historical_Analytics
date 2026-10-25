from __future__ import annotations

import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pandas as pd
from PySide6.QtCore import QEventLoop, QTimer
from PySide6.QtWidgets import QApplication

from spotify_historical_analytics.db import DatabaseManager
from spotify_historical_analytics.metadata_importer import import_metadata_dataframe
from spotify_historical_analytics.ui.main_window import MainWindow


TRACK_ID = "A" * 22
ALBUM_ID = "B" * 22
ARTIST_ID = "C" * 22


def wait_for_dashboard(window: MainWindow) -> None:
    if window._has_current_dashboard_payload():
        return
    loop = QEventLoop()
    timeout = QTimer()
    timeout.setSingleShot(True)
    timeout.timeout.connect(loop.quit)
    window.dashboard_updated.connect(loop.quit)
    timeout.start(10_000)
    loop.exec()
    window.dashboard_updated.disconnect(loop.quit)
    assert window._has_current_dashboard_payload()


def test_artist_and_album_pages_use_mapped_real_observations(tmp_path: Path) -> None:
    app = QApplication.instance() or QApplication([])
    db = DatabaseManager(tmp_path / "phase3_ui.db")
    db.register_chart_record(
        batch_id="real-fixture",
        source="User fixture",
        source_license="Authorized test fixture",
        chart_type="daily",
        country="US",
        chart_date="2024-05-01",
        weekly_start=None,
        weekly_end=None,
        position=4,
        track_id=TRACK_ID,
        track_name="Mapped UI Track",
        artist_names="Credited Artist",
        streams=12000,
        original_url=None,
    )
    db.register_chart_record(
        batch_id="real-fixture",
        source="User fixture",
        source_license="Authorized test fixture",
        chart_type="daily",
        country="US",
        chart_date="2024-05-02",
        weekly_start=None,
        weekly_end=None,
        position=7,
        track_id="D" * 22,
        track_name="Unmapped UI Track",
        artist_names="Unmapped credited artist",
        streams=8000,
        original_url=None,
    )
    window = MainWindow(db=db)
    window.show()
    wait_for_dashboard(window)

    window.navigate(3)
    app.processEvents()
    assert window.album_table.rowCount() == 0
    assert window.album_empty.isVisible()

    metadata = pd.DataFrame(
        [
            {
                "track_id": TRACK_ID,
                "album_id": ALBUM_ID,
                "album_name": "Mapped UI Album",
                "album_artist": "Album Artist",
                "artist_id": ARTIST_ID,
                "artist_name": "Mapped Artist",
            }
        ]
    )
    import_metadata_dataframe(
        db,
        metadata,
        "Authorized metadata",
        "Rights documented by test",
        "metadata.csv",
        {
            "track_id": "track_id",
            "album_id": "album_id",
            "album_name": "album_name",
            "album_artist": "album_artist",
            "artist_id": "artist_id",
            "artist_name": "artist_name",
        },
    )
    window.refresh_dashboard()
    wait_for_dashboard(window)
    window.navigate(2)
    app.processEvents()
    assert window.artist_table.rowCount() == 2
    assert window.artist_table.item(0, 1).text() == "Mapped Artist"
    assert window.artist_table.item(0, 2).text() == "12,000"

    window.navigate(3)
    app.processEvents()
    assert window.album_table.rowCount() == 1
    assert window.album_table.item(0, 1).text() == "Mapped UI Album"
    assert window.album_table.item(0, 3).text() == "12,000"

    window.start_edit.setDate(window.start_edit.date().fromString("2024-05-02", "yyyy-MM-dd"))
    window.end_edit.setDate(window.end_edit.date().fromString("2024-05-02", "yyyy-MM-dd"))
    window.apply_filters()
    wait_for_dashboard(window)
    assert window.album_table.rowCount() == 0
    assert window.artist_table.rowCount() == 1
    assert window.artist_table.item(0, 1).text() == "Unmapped credited artist"

    window.close()
