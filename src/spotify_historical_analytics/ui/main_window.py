from __future__ import annotations

from datetime import date, datetime, timedelta
import logging
from pathlib import Path
import tempfile

import pyqtgraph as pg
from PySide6.QtCore import QThread, QUrl, Qt, QTimer, Signal
from PySide6.QtGui import QCloseEvent, QCursor, QDesktopServices, QFont, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QComboBox,
    QDialogButtonBox,
    QDateEdit,
    QDialog,
    QFileDialog,
    QFrame,
    QFormLayout,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QHeaderView,
    QToolTip,
)

from ..config import APP_NAME, APP_VERSION, APP_ROOT, BACKUP_DIR, EXPORT_DIR, LOG_DIR
from ..db import DatabaseManager
from ..metadata_importer import (
    METADATA_FIELDS,
    REQUIRED_FIELDS,
    load_metadata_preview,
    suggest_metadata_columns,
)
from ..services.analytics import AnalyticsService
from ..resources import resource_path
from ..settings import SettingsStore
from .workers import (
    DashboardQueryWorker,
    DetailQueryWorker,
    ExportWorker,
    ImportWorker,
)


COLORS = {
    "background": "#0E1117",
    "sidebar": "#141923",
    "card": "#1B2230",
    "accent": "#8B5CF6",
    "accent_light": "#A78BFA",
    "text": "#F8FAFC",
    "muted": "#94A3B8",
    "border": "#293244",
    "green": "#34D399",
}

PAGES = [
    ("Overview", "◉", "overview"),
    ("Top Songs", "♫", "songs"),
    ("Top Artists", "♙", "artists"),
    ("Top Albums", "▤", "albums"),
    ("Data Sources & Coverage", "▦", "coverage"),
    ("Settings", "⚙", "settings"),
]


class KPIWidget(QFrame):
    def __init__(self, title: str, description: str) -> None:
        super().__init__()
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(9)
        self.title = QLabel(title.upper())
        self.title.setObjectName("eyebrow")
        self.value = QLabel("—")
        self.value.setObjectName("kpiValue")
        self.value.setWordWrap(True)
        self.value.setToolTip(description)
        self.subtitle = QLabel(description)
        self.subtitle.setObjectName("muted")
        self.subtitle.setWordWrap(True)
        layout.addWidget(self.title)
        layout.addWidget(self.value)
        layout.addWidget(self.subtitle)


class NumericTableItem(QTableWidgetItem):
    def __lt__(self, other: QTableWidgetItem) -> bool:
        left = self.data(Qt.UserRole)
        right = other.data(Qt.UserRole)
        if left is not None and right is not None:
            return float(left) < float(right)
        return super().__lt__(other)


class NavigationButton(QPushButton):
    def __init__(self, icon_text: str, label_text: str) -> None:
        super().__init__()
        self.setAccessibleName(label_text)
        self.setAccessibleDescription(f"Open the {label_text} page.")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 0, 8, 0)
        layout.setSpacing(12)
        icon = QLabel(icon_text)
        icon.setObjectName("navIcon")
        icon.setAlignment(Qt.AlignCenter)
        icon.setFixedWidth(22)
        icon.setAttribute(Qt.WA_TransparentForMouseEvents)
        label = QLabel(label_text)
        label.setObjectName("navLabel")
        label.setAttribute(Qt.WA_TransparentForMouseEvents)
        layout.addWidget(icon)
        layout.addWidget(label, 1)


class ChartPanel(QFrame):
    def __init__(self, title: str, subtitle: str = "") -> None:
        super().__init__()
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(7)
        heading = QLabel(title)
        heading.setObjectName("panelTitle")
        layout.addWidget(heading)
        self.subtitle = QLabel(subtitle)
        self.subtitle.setObjectName("muted")
        layout.addWidget(self.subtitle)
        self.plot = pg.PlotWidget(axisItems={"bottom": pg.DateAxisItem(orientation="bottom")})
        self.plot.setBackground(COLORS["card"])
        self.setMinimumHeight(280)
        self.plot.showGrid(x=True, y=True, alpha=0.16)
        self.plot.getAxis("left").setTextPen(COLORS["muted"])
        self.plot.getAxis("bottom").setTextPen(COLORS["muted"])
        self.plot.getAxis("left").setPen(COLORS["border"])
        self.plot.getAxis("bottom").setPen(COLORS["border"])
        self.plot.setMenuEnabled(True)
        self.empty = QLabel("No imported observations match these filters.")
        self.empty.setObjectName("emptyState")
        self.empty.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.plot, 1)
        layout.addWidget(self.empty, 1)
        self.set_empty(True)

    def set_empty(self, empty: bool, message: str | None = None) -> None:
        self.plot.setVisible(not empty)
        self.empty.setVisible(empty)
        if message:
            self.empty.setText(message)


class MetadataImportDialog(QDialog):
    def __init__(self, file_path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Import user-supplied metadata")
        self.resize(940, 680)
        self.file_path = file_path
        self.preview = load_metadata_preview(file_path)
        self.columns = [str(column) for column in self.preview.columns]
        suggestions = suggest_metadata_columns(self.columns)

        layout = QVBoxLayout(self)
        info = QLabel(
            "Mappings require exact stable Spotify IDs. The application will not infer mappings from similar names."
        )
        info.setWordWrap(True)
        info.setObjectName("muted")
        layout.addWidget(info)

        source_form = QFormLayout()
        self.source_name = QLineEdit(Path(file_path).stem)
        self.source_license = QLineEdit("User-supplied metadata; rights must be confirmed before use.")
        source_form.addRow("Metadata source", self.source_name)
        source_form.addRow("License / attribution note", self.source_license)
        layout.addLayout(source_form)

        mappings = QFrame()
        mappings.setObjectName("card")
        mapping_form = QFormLayout(mappings)
        self.mapping_combos: dict[str, QComboBox] = {}
        for field_name, aliases in METADATA_FIELDS.items():
            combo = QComboBox()
            combo.addItem("— Not provided —", "")
            for column in self.columns:
                combo.addItem(column, column)
            suggested = suggestions.get(field_name, "")
            if suggested:
                combo.setCurrentIndex(combo.findData(suggested))
            combo.setToolTip(
                "Required field" if field_name in REQUIRED_FIELDS
                else "Optional field; not used to guess missing identities"
            )
            self.mapping_combos[field_name] = combo
            label = field_name.replace("_", " ").title()
            if field_name in REQUIRED_FIELDS:
                label += " *"
            mapping_form.addRow(label, combo)
        layout.addWidget(mappings)

        preview_title = QLabel("Data preview (first 12 rows)")
        preview_title.setStyleSheet("font-weight:700;")
        layout.addWidget(preview_title)
        table = QTableWidget(len(self.preview), len(self.columns))
        table.setHorizontalHeaderLabels(self.columns)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setAlternatingRowColors(True)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        table.setMaximumHeight(210)
        for row_index, (_, row) in enumerate(self.preview.iterrows()):
            for column_index, column in enumerate(self.columns):
                table.setItem(row_index, column_index, QTableWidgetItem(str(row[column])))
        layout.addWidget(table)

        self.buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.buttons.accepted.connect(self._accept_if_valid)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

    def column_mapping(self) -> dict[str, str]:
        return {
            field_name: str(combo.currentData() or "")
            for field_name, combo in self.mapping_combos.items()
        }

    def source_details(self) -> tuple[str, str]:
        return self.source_name.text().strip(), self.source_license.text().strip()

    def _accept_if_valid(self) -> None:
        source_name, source_license = self.source_details()
        if not source_name or not source_license:
            QMessageBox.warning(self, "Metadata source required", "Provide a source name and a rights/attribution note.")
            return
        mapping = self.column_mapping()
        missing = [name for name in REQUIRED_FIELDS if not mapping.get(name)]
        has_album_mapping = bool(mapping.get("album_id") and mapping.get("album_name"))
        has_artist_mapping = bool(mapping.get("artist_id"))
        if missing or not (has_album_mapping or has_artist_mapping):
            if not missing:
                missing = ["album ID + album title or artist ID"]
            QMessageBox.warning(
                self,
                "Required columns missing",
                f"Map these fields before importing: {', '.join(missing)}.",
            )
            return
        self.accept()


class MainWindow(QMainWindow):
    dashboard_updated = Signal()

    def __init__(self, db: DatabaseManager | None = None) -> None:
        super().__init__()
        self.db = db or DatabaseManager()
        self.settings = SettingsStore()
        if self.settings.load_error:
            logging.getLogger("us_music_charts_analytics").error(self.settings.load_error)
            QMessageBox.warning(
                None,
                "Settings unavailable",
                "Saved import/export folder preferences could not be read. "
                "Default folders will be used; your database and chart records are unchanged.\n\n"
                f"Details: {self.settings.load_error}",
            )
        self._production_db = self.db
        self.analytics = AnalyticsService(self.db)
        self.active_start: str | None = None
        self.active_end: str | None = None
        self.active_chart_type = "daily"
        self._nav_buttons: list[QPushButton] = []
        self._import_thread: QThread | None = None
        self._import_worker: ImportWorker | None = None
        self._import_progress: QProgressDialog | None = None
        self._dashboard_generation = 0
        self._dashboard_payload: dict | None = None
        self._query_threads: dict[int, tuple[QThread, DashboardQueryWorker]] = {}
        self._detail_threads: dict[int, tuple[QThread, DetailQueryWorker]] = {}
        self._export_threads: dict[int, tuple[QThread, ExportWorker]] = {}
        self._detail_generation = 0
        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.setInterval(250)
        self._search_timer.timeout.connect(self.refresh_dashboard)
        self._demo_tempdir: tempfile.TemporaryDirectory[str] | None = None
        self._demo_db: DatabaseManager | None = None
        self._demo_mode = False
        self._build_ui()
        self._update_date_bounds()
        self.refresh_dashboard()

    def _build_ui(self) -> None:
        self.setWindowTitle(APP_NAME)
        self.setWindowIcon(QIcon(str(resource_path("assets/app_icon.ico"))))
        self.resize(1500, 920)
        self.setMinimumSize(1120, 700)
        self.setStyleSheet(
            f"""
            QWidget {{ color:{COLORS['text']}; font-family:'Segoe UI'; font-size:13px; }}
            QLabel {{ background:transparent; color:{COLORS['text']}; }}
            QMainWindow {{ background:{COLORS['background']}; }}
            QWidget#centralRoot, QWidget#mainContent, QScrollArea#contentScroll {{ background:{COLORS['background']}; }}
            QScrollArea#contentScroll {{ border:0; }}
            QFrame#sidebar {{ background:{COLORS['sidebar']}; border-right:1px solid {COLORS['border']}; }}
            QFrame#card {{ background:{COLORS['card']}; border:1px solid {COLORS['border']}; border-radius:12px; }}
            QLabel#muted {{ color:{COLORS['muted']}; font-size:11px; }}
            QLabel#eyebrow {{ color:{COLORS['muted']}; font-size:10px; font-weight:700; letter-spacing:1px; }}
            QLabel#kpiValue {{ color:{COLORS['text']}; font-size:25px; font-weight:700; }}
            QLabel#panelTitle {{ color:{COLORS['text']}; font-size:15px; font-weight:700; }}
            QLabel#emptyState {{ background:{COLORS['card']}; color:{COLORS['muted']}; padding:20px; border:1px dashed {COLORS['border']}; border-radius:10px; }}
            QPushButton {{ background:{COLORS['card']}; border:1px solid {COLORS['border']}; border-radius:7px; padding:8px 12px; color:{COLORS['text']}; }}
            QPushButton:hover {{ border-color:{COLORS['accent_light']}; background:#222B3B; }}
            QPushButton:focus {{ border:1px solid {COLORS['accent_light']}; }}
            QPushButton#primary {{ background:{COLORS['accent']}; border-color:{COLORS['accent']}; font-weight:600; }}
            QPushButton#primary:hover {{ background:{COLORS['accent_light']}; }}
            QPushButton#nav {{ text-align:left; background:transparent; border:0; border-radius:7px; padding:9px 0; color:{COLORS['muted']}; min-height:22px; }}
            QPushButton#nav:hover {{ background:#202838; color:{COLORS['text']}; }}
            QPushButton#nav[active="true"] {{ color:{COLORS['text']}; background:#26203B; border-left:3px solid {COLORS['accent']}; }}
            QPushButton#nav QLabel#navIcon, QPushButton#nav QLabel#navLabel {{ color:{COLORS['muted']}; }}
            QPushButton#nav[active="true"] QLabel#navIcon, QPushButton#nav[active="true"] QLabel#navLabel {{ color:{COLORS['text']}; }}
            QLineEdit, QComboBox, QDateEdit {{ background:#121823; border:1px solid {COLORS['border']}; border-radius:6px; padding:7px 9px; min-height:22px; }}
            QLineEdit:focus, QComboBox:focus, QDateEdit:focus {{ border-color:{COLORS['accent_light']}; }}
            QComboBox QAbstractItemView {{ background:#121823; selection-background-color:{COLORS['accent']}; }}
            QTableWidget {{ background:{COLORS['card']}; alternate-background-color:#202938; gridline-color:{COLORS['border']}; border:1px solid {COLORS['border']}; border-radius:8px; selection-background-color:#42316B; }}
            QHeaderView::section {{ background:#202938; color:{COLORS['muted']}; border:0; border-bottom:1px solid {COLORS['border']}; padding:9px; font-weight:600; }}
            QToolTip {{ background:#202938; color:{COLORS['text']}; border:1px solid {COLORS['border']}; padding:6px; }}
            """
        )

        central = QWidget()
        central.setObjectName("centralRoot")
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self.setCentralWidget(central)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(252)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(16, 22, 14, 18)
        side_layout.setSpacing(8)
        brand = QLabel("US MUSIC CHARTS\nANALYTICS")
        brand.setFont(QFont("Segoe UI", 15, QFont.Bold))
        brand.setObjectName("brand")
        brand.setStyleSheet(f"color:{COLORS['text']}; letter-spacing:1px; background:transparent;")
        side_layout.addWidget(brand)
        product = QLabel("US music chart intelligence")
        product.setObjectName("muted")
        side_layout.addWidget(product)
        side_layout.addSpacing(24)
        for index, (label, icon, _) in enumerate(PAGES):
            button = NavigationButton(icon, label)
            button.setObjectName("nav")
            button.setProperty("active", index == 0)
            button.setCursor(Qt.PointingHandCursor)
            button.clicked.connect(lambda checked=False, page=index: self.navigate(page))
            side_layout.addWidget(button)
            self._nav_buttons.append(button)
        side_layout.addStretch()
        version = QLabel(f"LOCAL DATA · v{APP_VERSION}")
        version.setObjectName("muted")
        side_layout.addWidget(version)
        root.addWidget(sidebar)

        content = QWidget()
        content.setObjectName("mainContent")
        content.setMinimumWidth(0)
        content.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(22, 20, 22, 18)
        content_layout.setSpacing(16)
        content_scroll = QScrollArea()
        content_scroll.setObjectName("contentScroll")
        content_scroll.setWidgetResizable(True)
        content_scroll.setFrameShape(QFrame.NoFrame)
        content_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content_scroll.setWidget(content)
        root.addWidget(content_scroll, 1)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        self.page_title = QLabel("Overview")
        self.page_title.setStyleSheet("font-size:26px; font-weight:700;")
        self.page_description = QLabel("Explore imported US chart observations and their reporting coverage.")
        self.page_description.setObjectName("muted")
        titles.addWidget(self.page_title)
        titles.addWidget(self.page_description)
        header.addLayout(titles)
        header.addStretch()
        self.market_badge = QLabel("●  UNITED STATES")
        self.market_badge.setStyleSheet(f"color:{COLORS['green']}; font-weight:700;")
        header.addWidget(self.market_badge)
        self.import_button = QPushButton("Import data")
        self.import_button.setObjectName("primary")
        self.import_button.clicked.connect(self.import_file)
        self.demo_button = QPushButton("Preview synthetic data")
        self.demo_button.clicked.connect(self.load_demo_data)
        self.refresh_button = QPushButton("Refresh")
        self.refresh_button.clicked.connect(self.refresh_dashboard)
        header.addWidget(self.import_button)
        header.addWidget(self.demo_button)
        header.addWidget(self.refresh_button)
        content_layout.addLayout(header)

        filters = QFrame()
        filters.setObjectName("card")
        filter_layout = QGridLayout(filters)
        filter_layout.setContentsMargins(12, 10, 12, 10)
        filter_layout.setHorizontalSpacing(9)
        filter_layout.setVerticalSpacing(7)
        filter_layout.addWidget(QLabel("CHART"), 0, 0)
        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItem("Daily", "daily")
        self.chart_type_combo.addItem("Weekly", "weekly")
        self.chart_type_combo.setMinimumWidth(108)
        self.chart_type_combo.currentIndexChanged.connect(self._chart_type_changed)
        self.chart_type_combo.setToolTip("Daily and weekly chart observations are analyzed separately.")
        filter_layout.addWidget(self.chart_type_combo, 0, 1)
        self.start_edit = QDateEdit()
        self.start_edit.setCalendarPopup(True)
        self.start_edit.setDisplayFormat("MMM d, yyyy")
        self.start_edit.setMinimumWidth(132)
        self.start_edit.setToolTip("Inclusive start date")
        filter_layout.addWidget(QLabel("FROM"), 0, 2)
        filter_layout.addWidget(self.start_edit, 0, 3)
        self.end_edit = QDateEdit()
        self.end_edit.setCalendarPopup(True)
        self.end_edit.setDisplayFormat("MMM d, yyyy")
        self.end_edit.setMinimumWidth(132)
        self.end_edit.setToolTip("Inclusive end date")
        filter_layout.addWidget(QLabel("TO"), 0, 4)
        filter_layout.addWidget(self.end_edit, 0, 5)
        apply_button = QPushButton("Apply")
        apply_button.setObjectName("primary")
        apply_button.clicked.connect(self.apply_filters)
        filter_layout.addWidget(apply_button, 0, 6)
        reset_button = QPushButton("All available")
        reset_button.clicked.connect(self.reset_filters)
        filter_layout.addWidget(reset_button, 0, 7)
        self.preset_combo = QComboBox()
        self.preset_combo.setMinimumWidth(160)
        self.preset_combo.addItem("Date presets", None)
        for label, days in [("Last 7 days", 7), ("Last 30 days", 30), ("Last 90 days", 90), ("Last year", 365)]:
            self.preset_combo.addItem(label, days)
        self.preset_combo.currentIndexChanged.connect(self._apply_preset)
        filter_layout.addWidget(self.preset_combo, 1, 0, 1, 2)
        self.data_status = QLabel("No imported chart data")
        self.data_status.setObjectName("muted")
        filter_layout.addWidget(self.data_status, 1, 2, 1, 6, Qt.AlignRight)
        filter_layout.setColumnStretch(3, 1)
        filter_layout.setColumnStretch(5, 1)
        content_layout.addWidget(filters)

        self.demo_banner = QLabel("DEMO / SYNTHETIC observations exist. They are excluded from all real-data metrics and charts.")
        self.demo_banner.setStyleSheet("background:#382B1E; color:#F7D8A1; padding:10px 12px; border:1px solid #71532C; border-radius:8px;")
        self.demo_banner.setVisible(False)
        content_layout.addWidget(self.demo_banner)

        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_overview_page())
        self.pages.addWidget(self._build_songs_page())
        self.pages.addWidget(self._build_artists_page())
        self.pages.addWidget(self._build_albums_page())
        self.pages.addWidget(self._build_coverage_page())
        self.pages.addWidget(self._build_settings_page())
        self.pages.setMinimumSize(0, 0)
        self.pages.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Expanding)
        self.song_export_button.setEnabled(not self._demo_mode)
        self.artist_export_button.setEnabled(not self._demo_mode)
        self.album_export_button.setEnabled(not self._demo_mode)
        content_layout.addWidget(self.pages, 1)

    def _build_overview_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(14)

        self.overview_data = QWidget()
        data_layout = QVBoxLayout(self.overview_data)
        data_layout.setContentsMargins(0, 0, 0, 0)
        data_layout.setSpacing(14)

        kpi_row = QHBoxLayout()
        kpi_row.setSpacing(12)
        definitions = [
            ("Available chart streams", "Sum of valid imported chart observations; not official platform totals."),
            ("Charting songs", "Unique track IDs where available; conservative name/artist fallback otherwise."),
            ("Credited artists", "Distinct credited artist strings present in imported observations."),
            ("Available chart dates", "Dates with at least one observation in the active filter."),
            ("Observed coverage", "Observed dates divided by expected intervals in the selected range; not completeness verification."),
        ]
        self.kpis = [KPIWidget(title, detail) for title, detail in definitions]
        for widget in self.kpis:
            kpi_row.addWidget(widget, 1)
        data_layout.addLayout(kpi_row)

        charts = QGridLayout()
        charts.setSpacing(12)
        self.streams_chart = ChartPanel("Streams over time", "Only observed dates are plotted; gaps are not converted to zero.")
        self.top_songs_chart = ChartPanel("Top 10 songs", "Ranked by available chart streams in the active date range.")
        charts.addWidget(self.streams_chart, 0, 0)
        charts.addWidget(self.top_songs_chart, 0, 1)
        charts.setColumnStretch(0, 3)
        charts.setColumnStretch(1, 2)
        data_layout.addLayout(charts, 1)
        layout.addWidget(self.overview_data, 1)

        self.overview_empty = QLabel("No historical chart data is loaded yet.")
        self.overview_empty.setObjectName("emptyState")
        self.overview_empty.setAlignment(Qt.AlignCenter)
        self.overview_empty.setWordWrap(True)
        layout.addWidget(self.overview_empty)

        self.overview_empty_actions = QWidget()
        actions_layout = QHBoxLayout(self.overview_empty_actions)
        actions_layout.setContentsMargins(0, 0, 0, 0)
        actions_layout.setSpacing(10)
        actions_layout.addStretch()
        import_authorized_button = QPushButton("Import Authorized Dataset")
        import_authorized_button.setObjectName("primary")
        import_authorized_button.clicked.connect(self.import_file)
        self.empty_import_button = import_authorized_button
        actions_layout.addWidget(import_authorized_button)
        preview_demo_button = QPushButton("Preview Demo Dashboard")
        preview_demo_button.clicked.connect(self.load_demo_data)
        self.empty_demo_button = preview_demo_button
        actions_layout.addWidget(preview_demo_button)
        view_sources_button = QPushButton("View Data Sources")
        view_sources_button.clicked.connect(lambda: self.navigate(4))
        self.empty_sources_button = view_sources_button
        actions_layout.addWidget(view_sources_button)
        actions_layout.addStretch()
        layout.addWidget(self.overview_empty_actions)

        self.overview_data.setVisible(False)
        self.overview_empty.setVisible(True)
        self.overview_empty_actions.setVisible(True)
        return page

    def _build_songs_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        intro = QLabel("Song rankings use stable track IDs when supplied. Unidentified tracks use exact title + credited artist matching.")
        intro.setObjectName("muted")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        controls = QHBoxLayout()
        self.song_search = QLineEdit()
        self.song_search.setPlaceholderText("Search songs or artists…")
        self.song_search.textChanged.connect(self._schedule_dashboard_refresh)
        controls.addWidget(self.song_search, 1)
        controls.addWidget(QLabel("SHOW"))
        self.song_limit = QComboBox()
        for limit in (50, 100, 200):
            self.song_limit.addItem(f"Top {limit}", limit)
        self.song_limit.currentIndexChanged.connect(self._schedule_dashboard_refresh)
        controls.addWidget(self.song_limit)
        export_button = QPushButton("Export…")
        export_button.setToolTip("Export the filtered Top Songs ranking to CSV or XLSX.")
        export_button.clicked.connect(lambda: self.export_rankings("songs"))
        self.song_export_button = export_button
        controls.addWidget(export_button)
        layout.addLayout(controls)
        self.songs_table = QTableWidget(0, 6)
        self.songs_table.setHorizontalHeaderLabels(["Rank", "Song", "Artist", "Total streams", "Best position", "Appearances"])
        self.songs_table.setAlternatingRowColors(True)
        self.songs_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.songs_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.songs_table.setSortingEnabled(True)
        self.songs_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.songs_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.songs_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.songs_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.songs_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.songs_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.songs_table.doubleClicked.connect(self._open_song_detail_from_selection)
        layout.addWidget(self.songs_table, 1)
        self.songs_empty = QLabel("No songs match the selected chart type and date range.")
        self.songs_empty.setObjectName("emptyState")
        self.songs_empty.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.songs_empty)
        return page

    def _build_artists_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        intro = QLabel(
            "Supplied artist IDs receive full credit for mapped charting-song streams. Unresolved credits remain grouped as the exact credited string; names are never split heuristically. Artist totals can overlap."
        )
        intro.setObjectName("muted")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        controls = QHBoxLayout()
        self.artist_search = QLineEdit()
        self.artist_search.setPlaceholderText("Search artist name or supplied ID…")
        self.artist_search.textChanged.connect(self._schedule_dashboard_refresh)
        controls.addWidget(self.artist_search, 1)
        controls.addWidget(QLabel("SHOW"))
        self.artist_limit = QComboBox()
        for limit in (50, 100, 200):
            self.artist_limit.addItem(f"Top {limit}", limit)
        self.artist_limit.currentIndexChanged.connect(self._schedule_dashboard_refresh)
        controls.addWidget(self.artist_limit)
        export_button = QPushButton("Export…")
        export_button.setToolTip("Export the filtered Top Artists ranking to CSV or XLSX.")
        export_button.clicked.connect(lambda: self.export_rankings("artists"))
        self.artist_export_button = export_button
        controls.addWidget(export_button)
        layout.addLayout(controls)
        self.artist_table = QTableWidget(0, 8)
        self.artist_table.setHorizontalHeaderLabels(
            ["Rank", "Artist / credited string", "Charting-song streams", "Charting tracks", "Chart appearances", "Best position", "First appearance", "Latest appearance"]
        )
        self.artist_table.setAlternatingRowColors(True)
        self.artist_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.artist_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.artist_table.setSortingEnabled(True)
        self.artist_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.artist_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for col in range(2, 8):
            self.artist_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.artist_table.doubleClicked.connect(self._open_artist_detail_from_selection)
        layout.addWidget(self.artist_table, 1)
        self.artist_empty = QLabel("No artist observations match the selected filters.")
        self.artist_empty.setObjectName("emptyState")
        self.artist_empty.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.artist_empty)
        return page

    def _build_albums_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        intro = QLabel(
            "Album charting-track streams are derived only from user-supplied stable track-ID to album-ID mappings. Editions with different album IDs remain separate."
        )
        intro.setObjectName("muted")
        intro.setWordWrap(True)
        layout.addWidget(intro)
        controls = QHBoxLayout()
        self.album_search = QLineEdit()
        self.album_search.setPlaceholderText("Search album title, artist, or ID…")
        self.album_search.textChanged.connect(self._schedule_dashboard_refresh)
        controls.addWidget(self.album_search, 1)
        controls.addWidget(QLabel("SHOW"))
        self.album_limit = QComboBox()
        for limit in (50, 100, 200):
            self.album_limit.addItem(f"Top {limit}", limit)
        self.album_limit.currentIndexChanged.connect(self._schedule_dashboard_refresh)
        controls.addWidget(self.album_limit)
        export_button = QPushButton("Export…")
        export_button.setToolTip("Export the filtered Top Albums ranking to CSV or XLSX.")
        export_button.clicked.connect(lambda: self.export_rankings("albums"))
        self.album_export_button = export_button
        controls.addWidget(export_button)
        layout.addLayout(controls)
        self.album_table = QTableWidget(0, 7)
        self.album_table.setHorizontalHeaderLabels(
            ["Rank", "Album", "Album artist", "Album charting-track streams", "Mapped tracks", "Chart appearances", "Best position"]
        )
        self.album_table.setAlternatingRowColors(True)
        self.album_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.album_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.album_table.setSortingEnabled(True)
        self.album_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.album_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.album_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        for col in range(3, 7):
            self.album_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        self.album_table.doubleClicked.connect(self._open_album_detail_from_selection)
        layout.addWidget(self.album_table, 1)
        self.album_empty = QLabel(
            "No album mappings are available for these filters. Import user-supplied metadata with matching stable Spotify track and album IDs in Settings."
        )
        self.album_empty.setObjectName("emptyState")
        self.album_empty.setWordWrap(True)
        self.album_empty.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.album_empty)
        return page

    def _phase_placeholder(self, title: str, description: str) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(28, 26, 28, 26)
        heading = QLabel(title)
        heading.setObjectName("panelTitle")
        heading.setWordWrap(True)
        text = QLabel(description)
        text.setObjectName("muted")
        text.setWordWrap(True)
        card_layout.addWidget(heading)
        card_layout.addWidget(text)
        card_layout.addStretch()
        layout.addWidget(card, 1)
        return page

    def _build_coverage_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        self.coverage_summary = QLabel("Coverage is descriptive only: imported rows do not establish source completeness.")
        self.coverage_summary.setObjectName("muted")
        self.coverage_summary.setWordWrap(True)
        layout.addWidget(self.coverage_summary)
        layout.addWidget(QLabel("Import sources and observed date ranges"))
        self.source_table = QTableWidget(0, 8)
        self.source_table.setHorizontalHeaderLabels(["Source", "Chart", "Market", "Rows", "Earliest", "Latest", "Data type", "License / rights note"])
        self.source_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.source_table.setAlternatingRowColors(True)
        self.source_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.source_table)
        layout.addWidget(QLabel("Coverage by year — completeness is unverified"))
        self.year_table = QTableWidget(0, 5)
        self.year_table.setHorizontalHeaderLabels(["Year", "Chart", "Observed dates", "Rows", "Assessment"])
        self.year_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.year_table.setAlternatingRowColors(True)
        self.year_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.year_table)
        self.missing_dates_label = QLabel("No missing dates to report.")
        self.missing_dates_label.setObjectName("muted")
        self.missing_dates_label.setWordWrap(True)
        layout.addWidget(self.missing_dates_label)
        return page

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        card = QFrame()
        card.setObjectName("card")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(22, 20, 22, 20)
        card_layout.setSpacing(12)
        heading = QLabel("Local data and backups")
        heading.setObjectName("panelTitle")
        card_layout.addWidget(heading)
        self.db_location = QLabel(str(self.db.db_path))
        self.db_location.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.db_location.setObjectName("muted")
        card_layout.addWidget(self.db_location)
        backup_button = QPushButton("Create database backup")
        self.backup_button = backup_button
        backup_button.clicked.connect(self.backup_database)
        card_layout.addWidget(backup_button, 0, Qt.AlignLeft)
        self.metadata_button = QPushButton("Import artist / album metadata")
        self.metadata_button.clicked.connect(self.import_metadata)
        card_layout.addWidget(self.metadata_button, 0, Qt.AlignLeft)
        self.mapping_summary_label = QLabel("")
        self.mapping_summary_label.setObjectName("muted")
        card_layout.addWidget(self.mapping_summary_label)
        self.storage_summary = QLabel(
            f"User data: {APP_ROOT}\n"
            f"Database: {self.db.db_path}\n"
            f"Backups: {BACKUP_DIR}\n"
            f"Exports: {EXPORT_DIR}\n"
            f"Logs: {LOG_DIR}"
        )
        self.storage_summary.setObjectName("muted")
        self.storage_summary.setWordWrap(True)
        self.storage_summary.setTextInteractionFlags(Qt.TextSelectableByMouse)
        card_layout.addWidget(self.storage_summary)
        open_data_button = QPushButton("Open data folder")
        open_data_button.clicked.connect(lambda: self._open_data_location(APP_ROOT))
        card_layout.addWidget(open_data_button, 0, Qt.AlignLeft)
        open_logs_button = QPushButton("Open logs folder")
        open_logs_button.clicked.connect(lambda: self._open_data_location(LOG_DIR))
        card_layout.addWidget(open_logs_button, 0, Qt.AlignLeft)
        about_button = QPushButton("About")
        about_button.clicked.connect(self.show_about)
        card_layout.addWidget(about_button, 0, Qt.AlignLeft)
        note = QLabel("Data remains on this computer. Confirm rights for every user-supplied source before commercial use.")
        note.setObjectName("muted")
        note.setWordWrap(True)
        card_layout.addWidget(note)
        card_layout.addStretch()
        layout.addWidget(card, 1)
        return page

    def navigate(self, page_index: int) -> None:
        self.pages.setCurrentIndex(page_index)
        self.page_title.setText(PAGES[page_index][0])
        descriptions = [
            "Explore imported US chart observations and their reporting coverage.",
            "Search, rank, and inspect imported charting songs.",
            "Compare credited artist totals from imported observations.",
            "Review album analytics availability.",
            "Inspect source provenance and observed historical coverage.",
            "Manage local data and backups.",
        ]
        self.page_description.setText(descriptions[page_index])
        for index, button in enumerate(self._nav_buttons):
            button.setProperty("active", index == page_index)
            button.style().unpolish(button)
            button.style().polish(button)
        if page_index == 1:
            cached = self._dashboard_payload.get("songs") if self._has_current_dashboard_payload() and not self.song_search.text().strip() else None
            self.refresh_songs_table(cached)
        elif page_index == 2:
            cached = self._dashboard_payload.get("artists") if self._has_current_dashboard_payload() and not self.artist_search.text().strip() else None
            self.refresh_artists_table(cached)
        elif page_index == 3:
            cached = self._dashboard_payload.get("albums") if self._has_current_dashboard_payload() and not self.album_search.text().strip() else None
            self.refresh_albums_table(cached)
        elif page_index == 4:
            if self._has_current_dashboard_payload():
                self.refresh_coverage_page(
                    self._dashboard_payload["inventory"],
                    self._dashboard_payload["coverage"],
                    self._dashboard_payload["mapping_summary"],
                )
            else:
                self._schedule_dashboard_refresh()

    def _open_data_location(self, path: Path) -> None:
        try:
            path.mkdir(parents=True, exist_ok=True)
            if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(path))):
                raise OSError(f"Windows could not open the folder: {path}")
        except OSError as exc:
            QMessageBox.warning(
                self,
                "Folder unavailable",
                f"Could not open this folder:\n{path}\n\n{exc}",
            )

    def show_about(self) -> None:
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"<h3>{APP_NAME}</h3>"
            f"<p>Version {APP_VERSION}</p>"
            "<p>Independent desktop software for analyzing user-supplied US chart data. "
            "Not affiliated with, endorsed by, or an official Spotify product.</p>"
            "<p>All rights to imported data remain subject to the applicable source terms.</p>",
        )

    def _last_directory(self, setting: str) -> str:
        saved = self.settings.get(setting)
        return str(Path(saved)) if saved and Path(saved).is_dir() else str(Path.home())

    def _remember_directory(self, setting: str, file_path: str) -> None:
        if file_path:
            try:
                self.settings.set(setting, str(Path(file_path).resolve().parent))
            except (OSError, RuntimeError) as exc:
                QMessageBox.warning(
                    self,
                    "Settings could not be saved",
                    f"The selected file remains available, but the last-used folder could not be saved:\n{exc}",
                )

    def _schedule_dashboard_refresh(self) -> None:
        self._dashboard_generation += 1
        self.statusBar().showMessage("Searching filtered results…")
        self._search_timer.start()

    def _chart_type_changed(self) -> None:
        self.active_chart_type = str(self.chart_type_combo.currentData() or "daily")
        self._update_date_bounds()
        self.refresh_dashboard()

    def _update_date_bounds(self) -> None:
        bounds = self.analytics.available_date_bounds(
            self.active_chart_type, include_demo=self._demo_mode
        )
        today = date.today()
        reporting_start = date(2017, 1, 1)
        earliest = date.fromisoformat(bounds["earliest"]) if bounds["earliest"] else None
        latest = date.fromisoformat(bounds["latest"]) if bounds["latest"] else None
        min_date = min(earliest, reporting_start) if earliest else reporting_start
        max_date = today
        if self.active_start:
            min_date = min(min_date, date.fromisoformat(self.active_start))
        if self.active_end:
            max_date = min(today, max(max_date, date.fromisoformat(self.active_end)))
        if min_date > max_date:
            min_date = max_date
        self.start_edit.setMinimumDate(min_date)
        self.start_edit.setMaximumDate(max_date)
        self.end_edit.setMinimumDate(min_date)
        self.end_edit.setMaximumDate(max_date)
        default_start = earliest if earliest and earliest <= today else reporting_start
        default_end = min(latest, today) if latest else today
        if earliest and earliest < reporting_start:
            self.start_edit.setToolTip(
                f"Imported observations begin on {earliest.isoformat()}, before the client default reporting window of 2017."
            )
        else:
            self.start_edit.setToolTip("Inclusive start date. The default reporting window begins January 1, 2017.")
        self.start_edit.setDate(
            date.fromisoformat(self.active_start) if self.active_start else default_start
        )
        self.end_edit.setDate(
            date.fromisoformat(self.active_end) if self.active_end else default_end
        )

    def _apply_preset(self) -> None:
        days = self.preset_combo.currentData()
        if days is None:
            return
        bounds = self.analytics.available_date_bounds(
            self.active_chart_type, include_demo=self._demo_mode
        )
        end = min(date.fromisoformat(bounds["latest"]), date.today()) if bounds["latest"] else date.today()
        start = end - timedelta(days=int(days) - 1)
        if bounds["earliest"]:
            start = max(start, date.fromisoformat(bounds["earliest"]))
        self.start_edit.setDate(start)
        self.end_edit.setDate(end)
        self.apply_filters()
        self.preset_combo.setCurrentIndex(0)

    def apply_filters(self) -> None:
        start = self.start_edit.date().toPython().isoformat()
        end = self.end_edit.date().toPython().isoformat()
        try:
            self.analytics.validate_date_range(start, end)
        except ValueError as exc:
            QMessageBox.warning(self, "Invalid date range", str(exc))
            return
        self.active_start = start
        self.active_end = end
        self.refresh_dashboard()

    def reset_filters(self) -> None:
        self.active_start = None
        self.active_end = None
        self._update_date_bounds()
        self.preset_combo.setCurrentIndex(0)
        self.refresh_dashboard()

    def _filters(self) -> dict[str, str | None]:
        return {
            "start_date": self.active_start,
            "end_date": self.active_end,
            "chart_type": self.active_chart_type,
        }

    def refresh_dashboard(self) -> None:
        self._search_timer.stop()
        self._dashboard_generation += 1
        generation = self._dashboard_generation
        self.statusBar().showMessage("Refreshing analytics in the background…")
        thread = QThread(self)
        worker = DashboardQueryWorker(
            db_path=str(self.db.db_path),
            generation=generation,
            start_date=self.active_start,
            end_date=self.active_end,
            chart_type=self.active_chart_type,
            song_search=self.song_search.text().strip() if hasattr(self, "song_search") else "",
            artist_search=self.artist_search.text().strip() if hasattr(self, "artist_search") else "",
            album_search=self.album_search.text().strip() if hasattr(self, "album_search") else "",
            song_limit=int(self.song_limit.currentData()) if hasattr(self, "song_limit") else 50,
            artist_limit=int(self.artist_limit.currentData()) if hasattr(self, "artist_limit") else 50,
            album_limit=int(self.album_limit.currentData()) if hasattr(self, "album_limit") else 50,
            include_demo=self._demo_mode,
        )
        worker.moveToThread(thread)
        thread.setProperty("dashboardGeneration", generation)
        thread.started.connect(worker.run)
        worker.completed.connect(self._on_dashboard_queries_completed)
        worker.failed.connect(self._on_dashboard_queries_failed)
        worker.completed.connect(thread.quit, Qt.DirectConnection)
        worker.failed.connect(thread.quit, Qt.DirectConnection)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._on_dashboard_query_thread_finished)
        thread.finished.connect(thread.deleteLater)
        self._query_threads[generation] = (thread, worker)
        thread.start()

    def _on_dashboard_queries_completed(self, payload: object) -> None:
        generation = payload["generation"]
        if generation != self._dashboard_generation:
            return
        self._dashboard_payload = payload
        overview = payload["overview"]
        inventory = payload["inventory"]
        summary = overview["summary"]
        values = [
            f"{summary['total_streams']:,}",
            f"{summary['distinct_tracks']:,}",
            f"{summary['distinct_artists']:,}",
            f"{summary['chart_dates_with_data']:,}",
            f"{summary['coverage_percentage']:.1f}%",
        ]
        for widget, value in zip(self.kpis, values):
            widget.value.setText(value)
        self.kpis[4].subtitle.setText(
            "Observed daily dates / selected calendar days" if self.active_chart_type == "daily"
            else "Observed weekly anchors / expected weekly intervals"
        )
        self.kpis[4].value.setToolTip("Descriptive observation coverage only; it does not verify that the source dataset is complete.")
        real_rows = int(inventory["summary"]["real_rows"] or 0)
        demo_rows = int(inventory["summary"]["demo_rows"] or 0)
        self.data_status.setText(f"{real_rows:,} real rows · {demo_rows:,} demo rows")
        if self._demo_mode:
            self.demo_banner.setText(
                "DEMO / SYNTHETIC MODE — isolated generated test records only. No production observations are shown."
            )
            self.demo_banner.setVisible(True)
        else:
            self.demo_banner.setText(
                "DEMO / SYNTHETIC observations exist in the isolated demo fixture and are excluded from real-data metrics."
            )
            self.demo_banner.setVisible(demo_rows > 0)
        has_active_data = demo_rows > 0 if self._demo_mode else real_rows > 0
        self.overview_data.setVisible(has_active_data)
        self.overview_empty.setVisible(not has_active_data)
        self.overview_empty_actions.setVisible(not has_active_data)
        self._render_streams_chart(payload["streams"])
        self._render_top_songs_chart(overview["top_tracks"])
        self.refresh_songs_table(payload["songs"])
        self.refresh_artists_table(payload["artists"])
        self.refresh_albums_table(payload["albums"])
        self.refresh_coverage_page(inventory, payload["coverage"], payload["mapping_summary"])
        if self._demo_mode:
            self.statusBar().showMessage("DEMO / SYNTHETIC mode: generated fixture data is isolated from production data.")
        elif real_rows:
            self.statusBar().showMessage("Charts and rankings reflect real imported observations only.")
        elif demo_rows:
            self.statusBar().showMessage("Only synthetic demo data exists. Real-data charts and rankings remain empty.")
        else:
            self.statusBar().showMessage("No chart observations imported. Import a CSV or XLSX file to begin.")
        self.dashboard_updated.emit()

    def _on_dashboard_queries_failed(self, error: object) -> None:
        generation, message = error
        if generation == self._dashboard_generation:
            self.statusBar().showMessage(f"Analytics could not be refreshed: {message}")

    def _on_dashboard_query_thread_finished(self) -> None:
        thread = self.sender()
        if thread is not None:
            self._query_threads.pop(int(thread.property("dashboardGeneration")), None)

    def _has_current_dashboard_payload(self) -> bool:
        return bool(
            self._dashboard_payload
            and self._dashboard_payload["generation"] == self._dashboard_generation
        )

    def _render_streams_chart(self, rows: list[dict]) -> None:
        plot = self.streams_chart.plot
        plot.clear()
        if not rows:
            self.streams_chart.set_empty(True)
            return
        points_x: list[float] = []
        points_y: list[float] = []
        previous: date | None = None
        cadence = 7 if self.active_chart_type == "weekly" else 1
        for row in rows:
            current = date.fromisoformat(row["chart_date"])
            if previous is not None and (current - previous).days > cadence:
                gap = previous + timedelta(days=cadence)
                points_x.append(datetime.combine(gap, datetime.min.time()).timestamp())
                points_y.append(float("nan"))
            points_x.append(datetime.combine(current, datetime.min.time()).timestamp())
            points_y.append(float(row["streams"]))
            previous = current
        line = pg.PlotDataItem(
            points_x,
            points_y,
            pen=pg.mkPen(COLORS["accent_light"], width=2),
            symbol="o",
            symbolSize=6,
            symbolBrush=COLORS["accent"],
            connect="finite",
        )
        plot.addItem(line)
        plot.setLabel("left", "Chart streams")
        plot.setLabel("bottom", "Chart date")
        plot.enableAutoRange()
        self.streams_chart.set_empty(False)
        self._stream_hover_proxy = pg.SignalProxy(plot.scene().sigMouseMoved, rateLimit=30, slot=self._show_stream_tooltip)
        self._stream_hover_rows = rows

    def _show_stream_tooltip(self, event: tuple) -> None:
        if not hasattr(self, "_stream_hover_rows"):
            return
        position = event[0]
        view = self.streams_chart.plot.getViewBox()
        if not self.streams_chart.plot.sceneBoundingRect().contains(position):
            return
        timestamp = view.mapSceneToView(position).x()
        rows = self._stream_hover_rows
        nearest = min(rows, key=lambda row: abs(datetime.fromisoformat(row["chart_date"]).timestamp() - timestamp))
        chart_date = nearest["chart_date"]
        period = ""
        if nearest.get("weekly_start") or nearest.get("weekly_end"):
            period = f"\nPeriod: {nearest.get('weekly_start') or chart_date} to {nearest.get('weekly_end') or chart_date}"
        QToolTip.showText(
            QCursor.pos(),
            f"{chart_date}{period}\n{int(nearest['streams']):,} chart streams",
            self.streams_chart,
        )

    def _render_top_songs_chart(self, rows: list[dict]) -> None:
        panel = self.top_songs_chart
        plot = panel.plot
        plot.clear()
        plot.getAxis("left").setTicks([])
        if not rows:
            panel.set_empty(True)
            return
        ranked = list(reversed(rows[:10]))
        y_values = list(range(len(ranked)))
        stream_values = [int(row["total_streams"]) for row in ranked]
        bars = pg.BarGraphItem(
            x0=[0] * len(ranked),
            x1=stream_values,
            y=y_values,
            height=0.62,
            brush=pg.mkBrush(COLORS["accent"]),
        )
        plot.addItem(bars)
        plot.getAxis("left").setTicks([[(index, row["track_name"]) for index, row in enumerate(ranked)]])
        plot.getAxis("left").setWidth(120)
        for index, value in enumerate(stream_values):
            label = pg.TextItem(f"{value:,}", color=COLORS["text"], anchor=(0, 0.5))
            label.setPos(value, index)
            plot.addItem(label)
        plot.setLabel("bottom", "Chart streams")
        plot.setYRange(-0.6, max(0.6, len(ranked) - 0.4), padding=0)
        plot.setXRange(0, max(stream_values) * 1.25 if max(stream_values) else 1, padding=0)
        panel.set_empty(False)

    def refresh_songs_table(self, rows: list[dict] | None = None) -> None:
        if not hasattr(self, "songs_table"):
            return
        if rows is None:
            self._schedule_dashboard_refresh()
            return
        table = self.songs_table
        table.setSortingEnabled(False)
        table.setRowCount(0)
        for rank, row in enumerate(rows, start=1):
            table.insertRow(rank - 1)
            cells = [
                NumericTableItem(str(rank)),
                QTableWidgetItem(str(row["track_name"])),
                QTableWidgetItem(str(row["artist_names"])),
                NumericTableItem(f"{int(row['total_streams']):,}"),
                NumericTableItem(str(row["best_position"] if row["best_position"] is not None else "—")),
                NumericTableItem(str(row["chart_appearances"])),
            ]
            for col, item in enumerate(cells):
                item.setData(Qt.UserRole, row["total_streams"] if col == 3 else (
                    rank if col == 0 else row["best_position"] if col == 4 else row["chart_appearances"] if col == 5 else None
                ))
                table.setItem(rank - 1, col, item)
            table.item(rank - 1, 1).setData(Qt.UserRole, row["track_key"])
        table.setSortingEnabled(True)
        table.sortItems(0, Qt.AscendingOrder)
        self.songs_empty.setVisible(not rows)
        table.setVisible(bool(rows))

    def _open_song_detail_from_selection(self) -> None:
        row_index = self.songs_table.currentRow()
        if row_index < 0:
            return
        key_item = self.songs_table.item(row_index, 1)
        if key_item is None:
            return
        track_key = key_item.data(Qt.UserRole)
        self._start_detail_query("songs", str(track_key))

    def _show_song_detail(self, detail: dict, rows: list[dict]) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Song details · {detail['track_name']}")
        dialog.resize(760, 560)
        layout = QVBoxLayout(dialog)
        heading = QLabel(detail["track_name"])
        heading.setStyleSheet("font-size:23px; font-weight:700;")
        artist = QLabel(detail["artist_names"] or "Artist metadata unavailable")
        artist.setObjectName("muted")
        layout.addWidget(heading)
        layout.addWidget(artist)
        metrics = QLabel(
            f"Streams: {int(detail['total_streams']):,}    "
            f"Best position: {detail['best_position'] if detail['best_position'] is not None else 'Unavailable'}    "
            f"Observed dates: {detail['observed_dates']}\n"
            f"First appearance: {detail['first_appearance']}    Latest: {detail['latest_appearance']}"
        )
        metrics.setWordWrap(True)
        layout.addWidget(metrics)
        panel = ChartPanel("Historical streams", "Observations shown for the active chart type and selected date range.")
        layout.addWidget(panel, 1)
        if rows:
            x = [datetime.fromisoformat(row["chart_date"]).timestamp() for row in rows]
            y = [int(row["streams"]) for row in rows]
            panel.plot.plot(x, y, pen=pg.mkPen(COLORS["accent_light"], width=2), symbol="o", symbolSize=7, symbolBrush=COLORS["accent"])
            panel.plot.setLabel("left", "Chart streams")
            panel.plot.setLabel("bottom", "Chart date")
            panel.set_empty(False)
        else:
            panel.set_empty(True, "No historical observations in the active filters.")
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button, 0, Qt.AlignRight)
        dialog.exec()

    def refresh_artists_table(self, rows: list[dict] | None = None) -> None:
        if not hasattr(self, "artist_table"):
            return
        if rows is None:
            self._schedule_dashboard_refresh()
            return
        table = self.artist_table
        table.setSortingEnabled(False)
        table.setRowCount(0)
        for index, row in enumerate(rows):
            table.insertRow(index)
            cells = [
                NumericTableItem(str(index + 1)),
                QTableWidgetItem(str(row["artist_name"] or "Artist metadata unavailable")),
                NumericTableItem(f"{int(row['charting_song_streams']):,}"),
                NumericTableItem(str(row["track_count"])),
                NumericTableItem(str(row["chart_appearances"])),
                NumericTableItem(str(row["best_position"] if row["best_position"] is not None else "—")),
                QTableWidgetItem(row["first_appearance"] or "—"),
                QTableWidgetItem(row["latest_appearance"] or "—"),
            ]
            for col, item in enumerate(cells):
                numeric = {
                    0: index + 1,
                    2: row["charting_song_streams"],
                    3: row["track_count"],
                    4: row["chart_appearances"],
                    5: row["best_position"],
                }.get(col)
                item.setData(Qt.UserRole, numeric)
                table.setItem(index, col, item)
            table.item(index, 1).setData(Qt.UserRole, row["artist_key"])
            table.item(index, 1).setToolTip(row["attribution"])
        table.setSortingEnabled(True)
        table.sortItems(0, Qt.AscendingOrder)
        table.setVisible(bool(rows))
        self.artist_empty.setVisible(not rows)

    def _open_artist_detail_from_selection(self) -> None:
        row_index = self.artist_table.currentRow()
        if row_index < 0:
            return
        artist_key = self.artist_table.item(row_index, 1).data(Qt.UserRole)
        self._start_detail_query("artists", str(artist_key))

    def _show_artist_detail(self, detail: dict, rows: list[dict]) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Artist details · {detail['artist_name']}")
        dialog.resize(780, 580)
        layout = QVBoxLayout(dialog)
        heading = QLabel(detail["artist_name"])
        heading.setStyleSheet("font-size:23px; font-weight:700;")
        identity = QLabel(
            f"{detail['attribution']} · artist ID: {detail['artist_id'] or 'not resolved'}"
        )
        identity.setObjectName("muted")
        identity.setWordWrap(True)
        layout.addWidget(heading)
        layout.addWidget(identity)
        stream_label = (
            "Full-credit charting-song streams"
            if detail["artist_id"]
            else "Exact credited-string chart streams"
        )
        metrics = QLabel(
            f"{stream_label}: {int(detail['charting_song_streams']):,}    "
            f"Tracks: {detail['track_count']}    Chart appearances: {detail['chart_appearances']}\n"
            f"Best position: {detail['best_position'] or 'Unavailable'}    "
            f"First: {detail['first_appearance']}    Latest: {detail['latest_appearance']}"
        )
        metrics.setWordWrap(True)
        layout.addWidget(metrics)
        panel = ChartPanel("Artist credited streams over time", "Full-credit mapped streams can overlap other artist totals.")
        self._populate_history_chart(panel, rows)
        layout.addWidget(panel, 1)
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button, 0, Qt.AlignRight)
        dialog.exec()

    def refresh_albums_table(self, rows: list[dict] | None = None) -> None:
        if not hasattr(self, "album_table"):
            return
        if rows is None:
            self._schedule_dashboard_refresh()
            return
        table = self.album_table
        table.setSortingEnabled(False)
        table.setRowCount(0)
        for index, row in enumerate(rows):
            table.insertRow(index)
            cells = [
                NumericTableItem(str(index + 1)),
                QTableWidgetItem(str(row["album_name"])),
                QTableWidgetItem(row["album_artist"] or "Album artist unavailable"),
                NumericTableItem(f"{int(row['charting_track_streams']):,}"),
                NumericTableItem(str(row["mapped_track_count"])),
                NumericTableItem(str(row["chart_appearances"])),
                NumericTableItem(str(row["best_position"] if row["best_position"] is not None else "—")),
            ]
            for col, item in enumerate(cells):
                numeric = {
                    0: index + 1,
                    3: row["charting_track_streams"],
                    4: row["mapped_track_count"],
                    5: row["chart_appearances"],
                    6: row["best_position"],
                }.get(col)
                item.setData(Qt.UserRole, numeric)
                table.setItem(index, col, item)
            table.item(index, 1).setData(Qt.UserRole, row["album_id"])
        table.setSortingEnabled(True)
        table.sortItems(0, Qt.AscendingOrder)
        table.setVisible(bool(rows))
        self.album_empty.setVisible(not rows)

    def _open_album_detail_from_selection(self) -> None:
        row_index = self.album_table.currentRow()
        if row_index < 0:
            return
        album_id = self.album_table.item(row_index, 1).data(Qt.UserRole)
        self._start_detail_query("albums", str(album_id))

    def _show_album_detail(self, detail: dict, tracks: list[dict], rows: list[dict]) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Album details · {detail['album_name']}")
        dialog.resize(900, 700)
        layout = QVBoxLayout(dialog)
        heading = QLabel(detail["album_name"])
        heading.setStyleSheet("font-size:23px; font-weight:700;")
        artist = QLabel(detail["album_artist"] or "Album artist unavailable")
        artist.setObjectName("muted")
        layout.addWidget(heading)
        layout.addWidget(artist)
        metrics = QLabel(
            f"Album charting-track streams: {int(detail['charting_track_streams']):,}    "
            f"Mapped tracks: {detail['mapped_track_count']}    "
            f"Chart appearances: {detail['chart_appearances']}    "
            f"Best position: {detail['best_position'] or 'Unavailable'}\n"
            f"First: {detail['first_appearance']}    Latest: {detail['latest_appearance']}    "
            f"Album ID: {detail['album_id']}    Release date: {detail['release_date'] or 'Unavailable'}"
        )
        metrics.setWordWrap(True)
        layout.addWidget(metrics)
        panel = ChartPanel("Album charting-track streams over time")
        self._populate_history_chart(panel, rows)
        layout.addWidget(panel, 1)
        track_table = QTableWidget(0, 5)
        track_table.setHorizontalHeaderLabels(["Track", "Credited artists", "Charting streams", "Appearances", "Best position"])
        track_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        track_table.setAlternatingRowColors(True)
        track_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        track_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for col in range(2, 5):
            track_table.horizontalHeader().setSectionResizeMode(col, QHeaderView.ResizeToContents)
        for index, track in enumerate(tracks):
            track_table.insertRow(index)
            values = [
                track["track_name"], track["artist_names"],
                f"{int(track['charting_track_streams']):,}", str(track["chart_appearances"]),
                str(track["best_position"] if track["best_position"] is not None else "—"),
            ]
            for col, value in enumerate(values):
                track_table.setItem(index, col, QTableWidgetItem(str(value or "")))
        layout.addWidget(track_table, 1)
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.accept)
        layout.addWidget(close_button, 0, Qt.AlignRight)
        dialog.exec()

    def _start_detail_query(self, kind: str, key: str) -> None:
        self._detail_generation += 1
        generation = self._detail_generation
        dashboard_generation = self._dashboard_generation
        self.statusBar().showMessage(f"Loading {kind[:-1] if kind.endswith('s') else kind} details…")
        thread = QThread(self)
        worker = DetailQueryWorker(
            db_path=str(self.db.db_path),
            generation=generation,
            kind=kind,
            key=key,
            start_date=self.active_start,
            end_date=self.active_end,
            chart_type=self.active_chart_type,
            dashboard_generation=dashboard_generation,
            include_demo=self._demo_mode,
        )
        worker.moveToThread(thread)
        thread.setProperty("detailGeneration", generation)
        thread.started.connect(worker.run)
        worker.completed.connect(self._on_detail_query_completed)
        worker.failed.connect(self._on_detail_query_failed)
        worker.completed.connect(thread.quit, Qt.DirectConnection)
        worker.failed.connect(thread.quit, Qt.DirectConnection)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._on_detail_query_thread_finished)
        thread.finished.connect(thread.deleteLater)
        self._detail_threads[generation] = (thread, worker)
        thread.start()

    def _on_detail_query_completed(self, payload: object) -> None:
        if (
            payload["generation"] != self._detail_generation
            or payload["dashboard_generation"] != self._dashboard_generation
        ):
            return
        detail = payload["detail"]
        if detail is None:
            QMessageBox.information(
                self, "Details", "No matching real-data observations are available in this filter."
            )
            return
        if payload["kind"] == "songs":
            self._show_song_detail(detail, payload["streams"])
        elif payload["kind"] == "artists":
            self._show_artist_detail(detail, payload["streams"])
        else:
            self._show_album_detail(detail, payload["tracks"], payload["streams"])

    def _on_detail_query_failed(self, error: object) -> None:
        generation, dashboard_generation, message = error
        if (
            generation == self._detail_generation
            and dashboard_generation == self._dashboard_generation
        ):
            QMessageBox.critical(self, "Details unavailable", str(message))

    def _on_detail_query_thread_finished(self) -> None:
        thread = self.sender()
        if thread is not None:
            self._detail_threads.pop(int(thread.property("detailGeneration")), None)

    def export_rankings(self, category: str) -> None:
        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            f"Export Top {category.title()}",
            str(Path(self._last_directory("last_export_directory")) / f"top-{category}.csv"),
            "CSV files (*.csv);;Excel workbooks (*.xlsx)",
        )
        if not file_path:
            return
        destination = Path(file_path)
        if destination.suffix.lower() not in {".csv", ".xlsx"}:
            destination = destination.with_suffix(
                ".xlsx" if "xlsx" in selected_filter.lower() else ".csv"
            )
        self._remember_directory("last_export_directory", str(destination))
        if category == "songs":
            limit = int(self.song_limit.currentData())
            search = self.song_search.text().strip() or None
        elif category == "artists":
            limit = int(self.artist_limit.currentData())
            search = self.artist_search.text().strip() or None
        elif category == "albums":
            limit = int(self.album_limit.currentData())
            search = self.album_search.text().strip() or None
        else:
            QMessageBox.warning(self, "Export unavailable", f"Unknown category: {category}")
            return

        thread = QThread(self)
        worker = ExportWorker(
            db_path=str(self.db.db_path),
            category=category,
            destination=str(destination),
            start_date=self.active_start,
            end_date=self.active_end,
            chart_type=self.active_chart_type,
            limit=limit,
            search=search,
        )
        worker.moveToThread(thread)
        thread.setProperty("exportGeneration", id(thread))
        thread.started.connect(worker.run)
        worker.progress.connect(self.statusBar().showMessage)
        worker.completed.connect(self._on_export_completed)
        worker.failed.connect(self._on_export_failed)
        worker.completed.connect(thread.quit, Qt.DirectConnection)
        worker.failed.connect(thread.quit, Qt.DirectConnection)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._on_export_thread_finished)
        thread.finished.connect(thread.deleteLater)
        self._export_threads[int(thread.property("exportGeneration"))] = (thread, worker)
        self.statusBar().showMessage(f"Exporting filtered Top {category.title()}…")
        thread.start()

    def _on_export_completed(self, result: object) -> None:
        QMessageBox.information(
            self,
            "Export complete",
            f"Exported {result['row_count']:,} ranking rows to:\n{result['destination']}",
        )

    def _on_export_failed(self, message: str) -> None:
        QMessageBox.critical(self, "Export failed", str(message))

    def _on_export_thread_finished(self) -> None:
        thread = self.sender()
        if thread is not None:
            self._export_threads.pop(int(thread.property("exportGeneration")), None)

    def _populate_history_chart(self, panel: ChartPanel, rows: list[dict]) -> None:
        panel.plot.clear()
        if not rows:
            panel.set_empty(True, "No real observations match the selected filters.")
            return
        x = [datetime.fromisoformat(row["chart_date"]).timestamp() for row in rows]
        y = [int(row["streams"]) for row in rows]
        panel.plot.plot(
            x, y, pen=pg.mkPen(COLORS["accent_light"], width=2),
            symbol="o", symbolSize=7, symbolBrush=COLORS["accent"],
        )
        panel.plot.setLabel("left", "Chart streams")
        panel.plot.setLabel("bottom", "Chart date")
        panel.set_empty(False)

    def refresh_coverage_page(
        self,
        inventory: dict | None = None,
        coverage: dict | None = None,
        mapping_summary: dict | None = None,
    ) -> None:
        if not hasattr(self, "source_table"):
            return
        inventory = inventory or self.analytics.data_inventory()
        mapping_summary = mapping_summary or self.db.get_metadata_mapping_summary()
        if hasattr(self, "mapping_summary_label"):
            self.mapping_summary_label.setText(
                f"Metadata mappings: {mapping_summary['artist_track_mappings']:,} artist-track · "
                f"{mapping_summary['album_track_mappings']:,} album-track · "
                f"{mapping_summary['unmapped_chart_track_ids']:,} chart track IDs without an album mapping."
            )
        summary = inventory["summary"]
        self.coverage_summary.setText(
            f"Real rows: {int(summary['real_rows'] or 0):,} · Synthetic rows: {int(summary['demo_rows'] or 0):,} · "
            f"Real data range: {summary['earliest_real'] or '—'} to {summary['latest_real'] or '—'}. "
            "All annual status values are unverified; observation counts do not prove complete source coverage."
        )
        self.source_table.setRowCount(0)
        for index, source in enumerate(inventory["sources"]):
            self.source_table.insertRow(index)
            values = [
                source["source"],
                source["chart_type"],
                source["country"],
                f"{source['row_count']:,}",
                source["earliest"] or "—",
                source["latest"] or "—",
                "Synthetic demo" if source["is_demo"] else "User supplied",
                source["source_license"] or "Not recorded",
            ]
            for col, value in enumerate(values):
                self.source_table.setItem(index, col, QTableWidgetItem(str(value)))
        source_index = len(inventory["sources"])
        for metadata_import in inventory["metadata_imports"]:
            self.source_table.insertRow(source_index)
            timestamp = metadata_import["created_at"]
            values = [
                f"{metadata_import['source_name']} · {metadata_import['file_name']}",
                "Metadata",
                "—",
                f"{metadata_import['imported_rows']:,}/{metadata_import['total_rows']:,} accepted",
                timestamp,
                timestamp,
                f"Rejected {metadata_import['rejected_rows']:,}; duplicates {metadata_import['duplicates_skipped']:,}",
                metadata_import["source_license"],
            ]
            for col, value in enumerate(values):
                self.source_table.setItem(source_index, col, QTableWidgetItem(str(value)))
            source_index += 1
        self.year_table.setRowCount(0)
        by_year_type = {(row["year"], row["chart_type"]): row for row in inventory["years"]}
        latest_year = max(
            [int(row["year"]) for row in inventory["years"]] + [date.today().year, 2017]
        )
        chart_types = {"daily", "weekly"}
        chart_types.update(row["chart_type"] for row in inventory["years"])
        index = 0
        for year_num in range(2017, latest_year + 1):
            for chart_type in sorted(chart_types):
                year = by_year_type.get((str(year_num), chart_type))
                values = [
                    str(year_num),
                    chart_type,
                    str(year["dates_with_data"]) if year else "0",
                    str(year["row_count"]) if year else "0",
                    "Unverified (observed)" if year else "No imported observations",
                ]
                self.year_table.insertRow(index)
                for col, value in enumerate(values):
                    self.year_table.setItem(index, col, QTableWidgetItem(value))
                index += 1
        coverage = coverage or self.db.get_coverage(self.active_chart_type)
        missing = coverage["missing_dates"]
        if missing:
            display = ", ".join(missing[:40])
            remaining = len(missing) - min(len(missing), 40)
            self.missing_dates_label.setText(
                f"Missing chart dates between first and last observed {self.active_chart_type} dates: "
                f"{display}" + (f" … and {remaining} more." if remaining else "")
            )
        else:
            self.missing_dates_label.setText(
                f"No gaps between observed {self.active_chart_type} dates, or there are not enough real observations to infer gaps."
            )

    def import_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import user-supplied chart data", self._last_directory("last_import_directory"),
            "Chart files (*.csv *.xlsx);;CSV files (*.csv);;Excel workbooks (*.xlsx)"
        )
        if not file_path:
            return
        self._remember_directory("last_import_directory", file_path)
        path = Path(file_path)
        try:
            self._start_import_worker(
                kind="chart",
                path=str(path),
                source_name=path.stem,
                source_license="User-supplied data. Rights must be confirmed before commercial use.",
            )
        except Exception as exc:
            QMessageBox.critical(self, "Import failed", f"The file could not be imported:\n{exc}")

    def import_metadata(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Import user-supplied artist / album metadata", self._last_directory("last_import_directory"),
            "Metadata files (*.csv *.xlsx);;CSV files (*.csv);;Excel workbooks (*.xlsx)"
        )
        if not file_path:
            return
        self._remember_directory("last_import_directory", file_path)
        try:
            dialog = MetadataImportDialog(file_path, self)
        except Exception as exc:
            QMessageBox.critical(self, "Metadata preview failed", str(exc))
            return
        if dialog.exec() != QDialog.Accepted:
            return
        source_name, source_license = dialog.source_details()
        self._start_import_worker(
            kind="metadata",
            path=file_path,
            source_name=source_name,
            source_license=source_license,
            column_mapping=dialog.column_mapping(),
        )

    def _start_import_worker(
        self,
        kind: str,
        path: str,
        source_name: str,
        source_license: str,
        column_mapping: dict[str, str] | None = None,
    ) -> None:
        if self._import_thread is not None:
            QMessageBox.information(self, "Import in progress", "Wait for the current import to finish before starting another.")
            return
        self.import_button.setEnabled(False)
        self.metadata_button.setEnabled(False)
        self._import_kind = kind
        self._import_progress = QProgressDialog(
            "Importing user-supplied data in the background…", "", 0, 0, self
        )
        self._import_progress.setWindowTitle("Import in progress")
        self._import_progress.setWindowModality(Qt.NonModal)
        self._import_progress.setCancelButton(None)
        self._import_progress.setMinimumDuration(0)
        self._import_progress.setLabelText(
            "Reading, validating, and importing transactionally. Cancellation is unavailable once import starts."
        )
        self._import_progress.show()

        thread = QThread(self)
        worker = ImportWorker(
            db_path=str(self.db.db_path),
            kind=kind,
            file_path=path,
            source_name=source_name,
            source_license=source_license,
            chart_type=self.active_chart_type,
            column_mapping=column_mapping,
        )
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._update_import_progress)
        worker.completed.connect(self._on_import_completed)
        worker.failed.connect(self._on_import_failed)
        worker.completed.connect(thread.quit, Qt.DirectConnection)
        worker.failed.connect(thread.quit, Qt.DirectConnection)
        thread.finished.connect(worker.deleteLater)
        thread.finished.connect(self._on_import_thread_finished)
        thread.finished.connect(thread.deleteLater)
        self._import_thread = thread
        self._import_worker = worker
        thread.start()

    def _update_import_progress(self, message: str) -> None:
        if self._import_progress is not None:
            self._import_progress.setLabelText(message)

    def _on_import_completed(self, result: object) -> None:
        if self._import_progress is not None:
            self._import_progress.close()
        if self._import_kind == "metadata":
            rejected_details = "\n".join(result.rejected_details[:10])
            QMessageBox.information(
                self,
                "Metadata import complete",
                f"Rows read: {result.total_rows:,}\n"
                f"Accepted: {result.imported_rows:,}\n"
                f"Rejected: {result.rejected_rows:,}\n"
                f"Existing mappings: {result.duplicates_skipped:,}\n"
                f"New album-track mappings: {result.album_track_mappings:,}\n"
                f"New artist-track mappings: {result.artist_track_mappings:,}"
                + (f"\n\nRejected rows:\n{rejected_details}" if rejected_details else ""),
            )
        else:
            rejected_details = "\n".join(result.rejected_details[:10])
            QMessageBox.information(
                self,
                "Chart import complete",
                f"Rows read: {result.total_rows:,}\nValid imported: {result.valid_rows:,}\n"
                f"Rejected: {result.rejected_rows:,}\nDuplicates skipped: {result.duplicates_skipped:,}"
                + (f"\n\nRejected rows:\n{rejected_details}" if rejected_details else ""),
            )
        self._update_date_bounds()
        self.refresh_dashboard()

    def _on_import_failed(self, message: str) -> None:
        if self._import_progress is not None:
            self._import_progress.close()
        QMessageBox.critical(self, "Import failed", f"The import was rolled back:\n{message}")

    def _on_import_thread_finished(self) -> None:
        self.import_button.setEnabled(True)
        self.metadata_button.setEnabled(True)
        if self._import_progress is not None:
            self._import_progress.close()
            self._import_progress.deleteLater()
        self._import_progress = None
        self._import_worker = None
        self._import_thread = None

    def load_demo_data(self) -> None:
        try:
            if self._import_thread is not None:
                QMessageBox.information(
                    self, "Import in progress", "Wait for the active import before changing datasets."
                )
                return
            if self._demo_mode:
                self._demo_mode = False
                self.db = self._production_db
                self.analytics = AnalyticsService(self.db)
                self.demo_button.setText("Preview synthetic data")
                self.import_button.setEnabled(True)
                self.metadata_button.setEnabled(True)
                self.backup_button.setEnabled(True)
                for button in (
                    self.song_export_button,
                    self.artist_export_button,
                    self.album_export_button,
                ):
                    button.setEnabled(True)
                (
                    self.active_start,
                    self.active_end,
                    chart_type,
                ) = self._saved_real_filters
                previous = self.chart_type_combo.blockSignals(True)
                self.chart_type_combo.setCurrentIndex(
                    max(0, self.chart_type_combo.findData(chart_type))
                )
                self.chart_type_combo.blockSignals(previous)
                self.active_chart_type = chart_type
                self.db_location.setText(str(self.db.db_path))
            else:
                self._saved_real_filters = (
                    self.active_start,
                    self.active_end,
                    self.active_chart_type,
                )
                if self._demo_db is None:
                    self._demo_tempdir = tempfile.TemporaryDirectory(
                        prefix="spotify-analytics-demo-"
                    )
                    self._demo_db = DatabaseManager(
                        Path(self._demo_tempdir.name) / "synthetic-demo.sqlite"
                    )
                    self._demo_db.seed_demo_dataset()
                self._demo_mode = True
                self.db = self._demo_db
                self.analytics = AnalyticsService(self.db)
                self.demo_button.setText("Return to real data")
                self.import_button.setEnabled(False)
                self.metadata_button.setEnabled(False)
                self.backup_button.setEnabled(False)
                for button in (
                    self.song_export_button,
                    self.artist_export_button,
                    self.album_export_button,
                ):
                    button.setEnabled(False)
                self.active_start = None
                self.active_end = None
                previous = self.chart_type_combo.blockSignals(True)
                self.chart_type_combo.setCurrentIndex(
                    max(0, self.chart_type_combo.findData("daily"))
                )
                self.chart_type_combo.blockSignals(previous)
                self.active_chart_type = "daily"
                self.db_location.setText(
                    "Temporary isolated DEMO / SYNTHETIC fixture"
                )
            self._update_date_bounds()
            self.refresh_dashboard()
        except Exception as exc:
            QMessageBox.critical(self, "Demo load failed", str(exc))

    def backup_database(self) -> None:
        default_backup = BACKUP_DIR / f"analytics-{datetime.now():%Y%m%d-%H%M%S}.db"
        destination, _ = QFileDialog.getSaveFileName(
            self, "Save database backup", str(default_backup), "SQLite database (*.db)"
        )
        if not destination:
            return
        try:
            self.db.backup_database(destination)
            self._remember_directory("last_backup_directory", destination)
            QMessageBox.information(self, "Backup complete", f"Database backup saved to:\n{destination}")
        except Exception as exc:
            QMessageBox.critical(self, "Backup failed", str(exc))

    def closeEvent(self, event: QCloseEvent) -> None:
        running_queries = [
            thread for thread, _ in self._query_threads.values() if thread.isRunning()
        ]
        running_queries.extend(
            thread for thread, _ in self._detail_threads.values() if thread.isRunning()
        )
        running_queries.extend(
            thread for thread, _ in self._export_threads.values() if thread.isRunning()
        )
        import_running = self._import_thread is not None and self._import_thread.isRunning()
        if import_running or running_queries:
            choice = QMessageBox.question(
                self,
                "Background task still running",
                "A background import or analytics query is running. Wait for it to finish before closing?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if choice == QMessageBox.StandardButton.No:
                event.ignore()
                return
            if import_running and self._import_thread is not None:
                self._import_thread.wait()
            for thread in running_queries:
                thread.wait()
        if self._demo_mode and self._demo_db is not None:
            self._demo_db.close()
            self._production_db.close()
        else:
            self._production_db.close()
            if self._demo_db is not None:
                self._demo_db.close()
        if self._demo_tempdir is not None:
            self._demo_tempdir.cleanup()
        event.accept()


if __name__ == "__main__":
    import sys

    application = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    raise SystemExit(application.exec())
