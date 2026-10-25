from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ..config import APP_NAME
from ..db import DatabaseManager
from ..importer import import_csv_file
from ..services.analytics import AnalyticsService


class KPIWidget(QWidget):
    def __init__(self, title: str, value: str, subtitle: str = "") -> None:
        super().__init__()
        self.title = QLabel(title)
        self.value = QLabel(value)
        self.subtitle = QLabel(subtitle)

        self.title.setStyleSheet("color:#b7b9c4; font-size:12px; font-weight:600; letter-spacing:0.06em;")
        self.value.setStyleSheet("color:#f2f3f8; font-size:26px; font-weight:700; margin-top:8px;")
        self.subtitle.setStyleSheet("color:#7f8597; font-size:11px; margin-top:8px;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.addWidget(self.title)
        layout.addWidget(self.value)
        layout.addWidget(self.subtitle)

        self.setStyleSheet(
            "QWidget { background:#1d1f2b; border:1px solid #2f3343; border-radius:10px; }"
        )


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.db = DatabaseManager()
        self.analytics = AnalyticsService(self.db)
        self.setWindowTitle(APP_NAME)
        self.resize(1600, 920)
        self._build_ui()
        self.refresh_dashboard()

    def _build_ui(self) -> None:
        self.setStyleSheet(
            """
            QWidget { background:#121522; color:#edf1ff; }
            QLabel { color:#edf1ff; }
            QMainWindow { background:#121522; }
            QPushButton { background:#2b2d42; border:1px solid #3d4251; border-radius:8px; padding:8px 12px; color:#edf1ff; }
            QPushButton:hover { background:#363b52; }
            QFrame { background:#171b2a; border:1px solid #262d42; border-radius:12px; }
            QTableWidget { background:#171b2a; color:#edf1ff; gridline-color:#2a3148; alternate-background-color:#1c2030; }
            QHeaderView::section { background:#20273e; color:#c9cce0; }
            """
        )

        central = QWidget(self)
        self.setCentralWidget(central)

        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)

        sidebar = QFrame()
        sidebar.setFixedWidth(230)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 18, 16, 18)
        sidebar_layout.setSpacing(12)

        title = QLabel(APP_NAME)
        title.setStyleSheet("font-size:20px; font-weight:700; letter-spacing:0.08em;")
        sidebar_layout.addWidget(title)

        self.nav_items = [
            ("Overview", "overview"),
            ("Songs", "songs"),
            ("Artists", "artists"),
            ("Albums", "albums"),
            ("Data Coverage", "coverage"),
            ("Settings", "settings"),
        ]
        for label, _ in self.nav_items:
            button = QPushButton(label)
            button.setCursor(Qt.PointingHandCursor)
            button.setStyleSheet(
                "QPushButton { text-align:left; background:#171b2a; border:none; padding:12px 14px; border-radius:8px; }"
                "QPushButton:hover { background:#222a3d; }"
            )
            sidebar_layout.addWidget(button)
        sidebar_layout.addStretch()

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(18)

        topbar = QHBoxLayout()
        self.page_title = QLabel("Overview")
        self.page_title.setStyleSheet("font-size:28px; font-weight:700;")
        topbar.addWidget(self.page_title)
        topbar.addStretch()

        self.import_csv_button = QPushButton("Import CSV")
        self.demo_button = QPushButton("Load demo data")
        self.refresh_button = QPushButton("Refresh")
        self.import_csv_button.clicked.connect(self.import_csv)
        self.demo_button.clicked.connect(self.load_demo_data)
        self.refresh_button.clicked.connect(self.refresh_dashboard)
        topbar.addWidget(self.import_csv_button)
        topbar.addWidget(self.demo_button)
        topbar.addWidget(self.refresh_button)
        content_layout.addLayout(topbar)

        self.demo_banner = QLabel(
            "DEMO / SYNTHETIC data is loaded for UI testing only and is excluded from real-data KPIs."
        )
        self.demo_banner.setVisible(False)
        self.demo_banner.setStyleSheet(
            "background:#3d2b1e; color:#f7d8a1; padding:12px 16px; border:1px solid #7c5522; border-radius:10px;"
        )
        content_layout.addWidget(self.demo_banner)

        self.kpi_layout = QHBoxLayout()
        self.kpi_layout.setSpacing(14)
        self.kpis = [
            KPIWidget("Total chart streams", "0", "Selected period"),
            KPIWidget("Distinct tracks", "0", "Charting tracks"),
            KPIWidget("Distinct artists", "0", "Credited artists"),
            KPIWidget("Chart dates with data", "0", "Coverage dates"),
            KPIWidget("Coverage", "0%", "Selected range"),
        ]
        for widget in self.kpis:
            self.kpi_layout.addWidget(widget)
        content_layout.addLayout(self.kpi_layout)

        table_wrapper = QFrame()
        table_layout = QVBoxLayout(table_wrapper)
        table_layout.setContentsMargins(14, 14, 14, 14)

        table_title = QLabel("Top songs in selected period")
        table_title.setStyleSheet("font-size:15px; font-weight:700; margin-bottom:8px;")
        table_layout.addWidget(table_title)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(["Song", "Artist", "Total streams", "Best position", "Appearances"])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(self.table.SelectRows)
        self.table.setEditTriggers(self.table.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 350)
        self.table.setColumnWidth(1, 220)
        self.table.setColumnWidth(2, 180)
        self.table.setColumnWidth(3, 120)
        self.table.setColumnWidth(4, 120)
        table_layout.addWidget(self.table)

        content_layout.addWidget(table_wrapper)

        root.addWidget(sidebar)
        root.addWidget(content, 1)

    def refresh_dashboard(self) -> None:
        overview = self.analytics.overview()
        summary = overview["summary"]
        self.page_title.setText("Overview")
        self._set_kpi_values(summary)

        self.demo_banner.setVisible(overview["has_demo_data"])
        if overview["has_demo_data"]:
            self.statusBar().showMessage("Showing demo data only. Real-data stats remain hidden until you import valid US chart files.")
        elif overview["has_real_data"]:
            self.statusBar().showMessage("Live imported data is available.")
        else:
            self.statusBar().showMessage("No valid US chart data available. Import a CSV file or load synthetic demo data.")

        self._render_top_tracks(overview["top_tracks"])

    def _set_kpi_values(self, summary: dict) -> None:
        self.kpis[0].value.setText(f"{summary['total_streams']:,}")
        self.kpis[1].value.setText(f"{summary['distinct_tracks']:,}")
        self.kpis[2].value.setText(f"{summary['distinct_artists']:,}")
        self.kpis[3].value.setText(f"{summary['chart_dates_with_data']:,}")
        self.kpis[4].value.setText(f"{summary['coverage_percentage']:.1f}%")

    def _render_top_tracks(self, rows: list[dict]) -> None:
        self.table.setRowCount(0)
        if not rows:
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem("No data available"))
            self.table.setItem(0, 1, QTableWidgetItem("—"))
            self.table.setItem(0, 2, QTableWidgetItem("0"))
            self.table.setItem(0, 3, QTableWidgetItem("—"))
            self.table.setItem(0, 4, QTableWidgetItem("0"))
            return

        for index, row in enumerate(rows):
            self.table.insertRow(index)
            self.table.setItem(index, 0, QTableWidgetItem(str(row.get("track_name", "Unknown"))))
            self.table.setItem(index, 1, QTableWidgetItem(str(row.get("artist_names", "Unknown"))))
            self.table.setItem(index, 2, QTableWidgetItem(f"{int(row.get('total_streams', 0)):,}"))
            self.table.setItem(index, 3, QTableWidgetItem(str(row.get("best_position", "—"))))
            self.table.setItem(index, 4, QTableWidgetItem(str(row.get("chart_appearances", 0))))

    def import_csv(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(self, "Select CSV file", str(Path.home()), "CSV Files (*.csv)")
        if not file_path:
            return
        try:
            result = import_csv_file(
                db=self.db,
                csv_path=file_path,
                source_name="User imported CSV",
                source_license="User-supplied data. Rights must be confirmed before commercial use.",
                chart_type="daily",
                country="US",
            )
            if result.valid_rows == 0:
                QMessageBox.warning(self, "Import issue", "No valid US rows were imported. Check the file schema or source region.")
            else:
                QMessageBox.information(self, "Import complete", f"Imported {result.valid_rows} valid rows from {file_path}.")
            self.refresh_dashboard()
        except Exception as exc:  # pragma: no cover - UI catch-all for user feedback
            QMessageBox.critical(self, "Import failed", f"The file could not be imported: {exc}")

    def load_demo_data(self) -> None:
        batch = self.db.seed_demo_dataset()
        self.statusBar().showMessage(f"Demo dataset loaded with batch {batch}.")
        self.refresh_dashboard()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec())
