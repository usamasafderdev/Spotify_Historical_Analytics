from __future__ import annotations

from itertools import islice
from pathlib import Path
import threading
import gzip
import zipfile
import errno
import time

from PySide6.QtCore import QObject, QThread, Qt, Signal, Slot
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QFileDialog, QFormLayout, QGroupBox,
    QHBoxLayout, QLabel, QLineEdit, QProgressBar, QPushButton, QScrollArea,
    QVBoxLayout, QWidget, QSizePolicy,
)

from ..runtime import LOGGER
from ..db import DatabaseManager
from ..import_sessions import FIELD_ALIASES, ImportSessionStore
from .theme import DIALOG_STYLE, apply_dark_theme


class ImportTask(QObject):
    inspected = Signal(object)
    completed = Signal(object)
    failed = Signal(str)
    progress = Signal(int, str)

    def __init__(self, staging, production, cancel, operation, **options):
        super().__init__()
        self.staging, self.production = str(staging), str(production)
        self.cancel, self.operation, self.options = cancel, operation, options

    @Slot()
    def run(self):
        store = database = None
        try:
            store = ImportSessionStore(self.staging)
            if self.operation == "preview":
                cadence = self.options["cadence"]
                session = store.create_session(
                    self.options["path"], self.options["source"],
                    "User-selected local dataset; source terms apply. Permissions not independently verified.",
                    cadence,
                )
                inspection = store.inspect_file(session)
                headers, rows = next(store._read_rows(Path(self.options["path"])))
                try:
                    sample = list(islice(rows, 200))
                finally:
                    rows.close()
                schema = self.options["mapping"] if self.options.get("mapping") is not None else inspection["schema"]
                observed = {str(row.get(schema.get("chart_type"), "")).strip().lower() for row in sample}
                explicit = observed & {"daily", "weekly"}
                detected = "daily" if inspection["adapter"] != "Compatible table" else (
                    next(iter(explicit)) if len(explicit) == 1 else None
                )
                if not detected and schema.get("weekly_start") and schema.get("weekly_end"):
                    detected = "weekly"
                if self.options["auto_cadence"] and detected:
                    cadence = detected
                    with store.connection:
                        store.connection.execute("UPDATE import_sessions SET chart_type=? WHERE session_id=?", (cadence, session))
                note = ("mixed daily/weekly; imports selected cadence only" if len(explicit) > 1 else
                        f"selected; source declares {detected}" if detected and detected != cadence else
                        "detected" if detected else "selected; cadence not explicit in sample")
                inspection.update(session_id=session, cadence=cadence, schema=schema, cadence_note=note)
                self.inspected.emit(inspection)
                if self.cancel.is_set():
                    self.completed.emit({"cancelled": True})
                    return
                try:
                    store._validate_schema(schema, headers)
                except ValueError as exc:
                    self.completed.emit({"inspection": inspection, "mapping_required": str(exc)})
                    return
                summary = store.prepare(session, self.cancel, self.progress.emit, schema)
                self.completed.emit({"inspection": inspection, "summary": summary,
                                     "cancelled": summary.status == "paused"})
            else:
                if self.cancel.is_set():
                    self.completed.emit({"cancelled": True})
                    return
                database = DatabaseManager(self.production)
                backup = Path(self.production).parent / "backups" / f"before-import-{time.time_ns()}.db"
                self.progress.emit(0, "Creating database backup")
                database.backup_database(backup)
                database.connection.set_progress_handler(lambda: int(self.cancel.is_set()), 1000)
                try:
                    result = store.finalize(self.options["session_id"], database, self.progress.emit, self.cancel)
                finally:
                    database.connection.set_progress_handler(None, 0)
                result["backup_path"] = str(backup)
                self.completed.emit({"result": result})
        except Exception as exc:
            if self.cancel.is_set():
                self.completed.emit({"cancelled": True})
            else:
                LOGGER.exception("Dataset %s failed", self.operation)
                if isinstance(exc, (gzip.BadGzipFile, EOFError)):
                    message = "The compressed CSV could not be read. Choose a valid CSV.GZ file."
                elif isinstance(exc, zipfile.BadZipFile):
                    message = "The Excel workbook could not be read. Choose a valid XLSX file."
                elif isinstance(exc, UnicodeDecodeError):
                    message = "The CSV text encoding is not supported. Save it as UTF-8 and try again."
                elif isinstance(exc, PermissionError):
                    message = "File access was denied. Check access to the selected file and destination folder."
                elif isinstance(exc, OSError) and exc.errno == errno.ENOSPC:
                    message = "There is not enough free disk space to complete this operation."
                else:
                    message = str(exc)
                self.failed.emit(message)
        finally:
            if database is not None:
                database.close()
            if store is not None:
                store.close()


class ImportDialog(QDialog):
    """One local-file import surface; validation and writes use separate databases."""

    def __init__(self, production_db_path, staging_db_path, parent=None):
        super().__init__(parent)
        apply_dark_theme(QApplication.instance())
        self.setStyleSheet(DIALOG_STYLE)
        self.production_db_path, self.staging_db_path = str(production_db_path), str(staging_db_path)
        self._thread = self._worker = None
        self._cancel = threading.Event()
        self._closing = False
        self._operation = ""
        self._summary = self._inspection = None
        self.imported = False
        self.result = None
        self.setWindowTitle("Import Historical Music Data")
        self.setMinimumSize(560, 400)
        screen = self.screen().availableGeometry()
        self.resize(min(840, screen.width() - 48), min(720, screen.height() - 64))
        outer = QVBoxLayout(self)
        heading = QLabel("Import Historical Music Data")
        heading.setStyleSheet("font-size:20px; font-weight:700;")
        outer.addWidget(heading)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        content = QWidget()
        content.setObjectName("importContent")
        content.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        body = QVBoxLayout(content)
        body.setSpacing(12)
        body.setAlignment(Qt.AlignTop)
        self.scroll.setWidget(content)
        outer.addWidget(self.scroll, 1)
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Choose a CSV, XLSX, or CSV.GZ dataset")
        self.browse_button = QPushButton("Browse Files")
        self.browse_button.clicked.connect(self.browse)
        file_row = QHBoxLayout()
        file_row.addWidget(self.path_edit, 1)
        file_row.addWidget(self.browse_button)
        body.addLayout(file_row)
        form = QFormLayout()
        form.setVerticalSpacing(12)
        form.setHorizontalSpacing(18)
        form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.source_edit = QLineEdit()
        self.cadence_combo = QComboBox()
        self.cadence_combo.addItem("Daily", "daily")
        self.cadence_combo.addItem("Weekly", "weekly")
        self.format_label = QLabel("Select a file to detect its format and schema.")
        self.coverage_label = QLabel("Not yet validated")
        self.records_label = QLabel("Not yet counted")
        self.usa_label = QLabel("Not yet counted")
        self.cadence_label = QLabel("Not yet detected")
        for title, widget in [("Dataset source", self.source_edit), ("File format / schema", self.format_label),
                              ("Date coverage", self.coverage_label), ("Total records", self.records_label),
                              ("USA records", self.usa_label), ("Chart cadence", self.cadence_combo),
                              ("Cadence detection", self.cadence_label)]:
            form.addRow(title, widget)
        body.addLayout(form)
        self.mapping_toggle = QPushButton("Show column mapping (optional)")
        self.mapping_toggle.setCheckable(True)
        self.mapping_toggle.hide()
        body.addWidget(self.mapping_toggle)
        self.mapping_section = QGroupBox("Column mapping")
        self.mapping_section.hide()
        mapping_layout = QVBoxLayout(self.mapping_section)
        self.mapping_content = QWidget()
        mapping_form = QFormLayout(self.mapping_content)
        mapping_form.setVerticalSpacing(10)
        mapping_form.setHorizontalSpacing(18)
        mapping_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        mapping_form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.optional_mapping_content = QWidget()
        optional_form = QFormLayout(self.optional_mapping_content)
        optional_form.setVerticalSpacing(10)
        optional_form.setHorizontalSpacing(18)
        optional_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        optional_form.setRowWrapPolicy(QFormLayout.WrapLongRows)
        self.mapping_combos = {}
        titles = {"date": "Date *", "track_name": "Track name *", "artist_names": "Artist credit *",
                  "streams": "Streams *", "country": "Country / region *"}
        for field in FIELD_ALIASES:
            combo = QComboBox()
            self.mapping_combos[field] = combo
            target = mapping_form if field in titles else optional_form
            target.addRow(titles.get(field, field.replace("_", " ").capitalize()), combo)
            combo.currentIndexChanged.connect(self._mapping_changed)
        mapping_layout.addWidget(self.mapping_content)
        self.optional_mapping_toggle = QPushButton("Show optional chart and metadata fields")
        self.optional_mapping_toggle.setCheckable(True)
        self.optional_mapping_toggle.toggled.connect(self.optional_mapping_content.setVisible)
        mapping_layout.addWidget(self.optional_mapping_toggle)
        mapping_layout.addWidget(self.optional_mapping_content)
        self.optional_mapping_content.hide()
        self.validate_button = QPushButton("Validate Mapping")
        self.validate_button.clicked.connect(lambda: self.preview(use_mapping=True, auto_cadence=False))
        mapping_layout.addWidget(self.validate_button)
        self.mapping_toggle.toggled.connect(self._toggle_mapping)
        body.addWidget(self.mapping_section)
        self.warnings = QLabel("Select a dataset to preview validation results.")
        self.warnings.setObjectName("validationWarnings")
        self.warnings.setStyleSheet("color:#FDE68A;")
        body.addWidget(self.warnings)
        self.result_label = QLabel("")
        self.result_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        body.addWidget(self.result_label)
        notice = QLabel("Import only data you are permitted to use. Files stay local; importing does not grant commercial or redistribution rights.")
        body.addWidget(notice)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        outer.addWidget(self.progress)
        self.status = QLabel("Choose a dataset to begin.")
        outer.addWidget(self.status)
        actions = QHBoxLayout()
        actions.addStretch()
        self.import_button = QPushButton("Import Dataset")
        self.import_button.setObjectName("primary")
        self.import_button.setEnabled(False)
        self.import_button.clicked.connect(self.start_import)
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        actions.addWidget(self.import_button)
        actions.addWidget(self.cancel_button)
        outer.addLayout(actions)
        for button in self.findChildren(QPushButton):
            button.setAutoDefault(False)
        self.import_button.setDefault(True)
        for label in self.findChildren(QLabel):
            label.setWordWrap(True)
            label.setTextFormat(Qt.PlainText)
        self.path_edit.textChanged.connect(self._invalidate)
        self.path_edit.editingFinished.connect(self._path_edited)
        self.source_edit.textEdited.connect(self._invalidate)
        self.source_edit.editingFinished.connect(self._source_edited)
        self.cadence_combo.currentIndexChanged.connect(lambda: self.preview(auto_cadence=False))

    def _toggle_mapping(self, checked):
        self.mapping_section.setVisible(checked)
        self.mapping_toggle.setText("Hide column mapping" if checked else "Show column mapping (optional)")

    def _invalidate(self, *_):
        self._summary = None
        self.import_button.setEnabled(False)

    def _path_edited(self):
        if self.path_edit.text().strip():
            self.preview()

    def _source_edited(self):
        if self._summary is None and self.path_edit.text().strip():
            self.preview(auto_cadence=False)

    def browse(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select music chart dataset", self.path_edit.text(),
                                             "Chart datasets (*.csv *.xlsx *.csv.gz)")
        if path:
            self.select_file(path)

    def select_file(self, path):
        for combo in self.mapping_combos.values():
            combo.blockSignals(True)
            combo.clear()
            combo.blockSignals(False)
        self.mapping_toggle.setChecked(False)
        self.path_edit.setText(str(path))
        self.source_edit.setText(Path(path).name.removesuffix(".gz").rsplit(".", 1)[0])
        self.preview()

    def preview(self, use_mapping=False, auto_cadence=True):
        if self._thread is not None:
            return
        self._invalidate()
        self.result_label.clear()
        self._inspection = None
        self.result = None
        self.format_label.setText("Detecting…")
        self.coverage_label.setText("Validating…")
        self.records_label.setText("Counting…")
        self.usa_label.setText("Counting…")
        self.mapping_section.hide()
        self.mapping_toggle.hide()
        path = self.path_edit.text().strip()
        if not self.source_edit.text().strip() and path:
            self.source_edit.setText(Path(path).name.removesuffix(".gz").rsplit(".", 1)[0])
        mapping = {field: combo.currentData() for field, combo in self.mapping_combos.items() if combo.currentData()} if use_mapping else None
        self._start("preview", path=path, source=self.source_edit.text().strip(),
                    cadence=self.cadence_combo.currentData(), auto_cadence=auto_cadence, mapping=mapping)

    def _start(self, operation, **options):
        self._operation = operation
        self._cancel.clear()
        self.progress.setRange(0, 0)
        self.status.setText("Detecting and validating dataset…" if operation == "preview" else "Importing dataset…")
        for control in (self.path_edit, self.browse_button, self.source_edit, self.cadence_combo, self.mapping_section, self.mapping_toggle):
            control.setEnabled(False)
        self.import_button.setEnabled(False)
        self._thread = QThread(self)
        self._worker = ImportTask(self.staging_db_path, self.production_db_path, self._cancel, operation, **options)
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.inspected.connect(self._inspected)
        self._worker.completed.connect(self._completed)
        self._worker.failed.connect(self._failed)
        self._worker.progress.connect(self._progress)
        self._worker.completed.connect(self._thread.quit, Qt.DirectConnection)
        self._worker.failed.connect(self._thread.quit, Qt.DirectConnection)
        self._thread.finished.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._finished)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def _inspected(self, inspection):
        self._inspection = inspection
        self.format_label.setText(f"{inspection['format'].upper()} · {inspection['adapter']}")
        self.cadence_label.setText(f"{inspection['cadence'].capitalize()} ({inspection['cadence_note']})")
        self.cadence_combo.blockSignals(True)
        self.cadence_combo.setCurrentIndex(self.cadence_combo.findData(inspection["cadence"]))
        self.cadence_combo.blockSignals(False)
        if inspection["adapter"] == "Compatible table":
            self.mapping_toggle.show()
            self.mapping_section.setVisible(self.mapping_toggle.isChecked())
            for field, combo in self.mapping_combos.items():
                combo.blockSignals(True)
                selected = inspection["schema"].get(field)
                combo.clear()
                combo.addItem("Not mapped", "")
                for header in inspection["headers"]:
                    combo.addItem(header, header)
                combo.setCurrentIndex(max(0, combo.findData(selected)))
                combo.blockSignals(False)

    def _mapping_changed(self, *_):
        if self._thread is None:
            self._invalidate()
            self.status.setText("Mapping changed. Click Validate Mapping to refresh the preview.")

    def _completed(self, payload):
        if payload.get("result") is not None:
            self.result = payload["result"]
            self.imported = True
            self.result_label.setText(
                f"Successfully imported records: {self.result['imported_rows']:,}\n"
                f"Skipped duplicate records: {self.result['duplicates_skipped']:,}\n"
                f"Rejected invalid records: {self._summary.rejected_rows:,}\n"
                "Import errors: none. Database integrity: OK."
            )
            self.status.setText("Import complete. A database backup was saved before importing.")
            self.cancel_button.setText("Close")
            self.mapping_toggle.setChecked(False)
            self.scroll.ensureWidgetVisible(self.result_label)
        elif payload.get("cancelled"):
            self._summary = None
            self.status.setText("Cancelled safely. No partial import was committed.")
        elif payload.get("mapping_required"):
            self.warnings.setText(payload["mapping_required"])
            self.mapping_toggle.setChecked(True)
            self.mapping_section.show()
            self.coverage_label.setText("Map columns first")
            self.records_label.setText("Not yet validated")
            self.usa_label.setText("Not yet validated")
            self.status.setText("Map the missing fields, then click Validate Mapping.")
        else:
            self._summary = payload["summary"]
            summary = self._summary
            self.coverage_label.setText(f"{summary.first_date or 'No valid dates'} — {summary.last_date or 'No valid dates'}")
            self.records_label.setText(f"{summary.processed_rows:,}")
            self.usa_label.setText(f"{summary.country_counts.get('US', 0):,} valid USA records")
            reasons = ", ".join(f"{reason}: {count:,}" for reason, count in summary.rejection_counts.items())
            self.warnings.setText(f"Rejected records: {summary.rejected_rows:,}. Duplicates: {summary.exact_duplicates:,}. Conflicts: {summary.conflicts:,}."
                                  + (f"\n{reasons}" if reasons else ""))
            self.status.setText("Ready to import." if summary.accepted_rows and not summary.conflicts else "Import blocked: no valid USA records or conflicting observations.")

    def _failed(self, message):
        self._summary = None
        self.warnings.setText(message)
        self.status.setText(("Import failed: " if self._operation == "import" else "Validation failed: ") + message)
        if self._operation == "preview":
            if self._inspection is None:
                self.format_label.setText("Unavailable")
                self.cadence_label.setText("Not detected")
            self.coverage_label.setText("Unavailable")
            self.records_label.setText("Unavailable")
            self.usa_label.setText("Unavailable")
        self.result_label.setText(f"Import errors: {message}")

    def _progress(self, count, message):
        self.status.setText(f"{message} · {count:,} records")

    def _finished(self):
        self._thread = self._worker = None
        self.progress.setRange(0, 100)
        self.progress.setValue(100 if self.result is not None or self._summary is not None else 0)
        for control in (self.path_edit, self.browse_button, self.source_edit, self.cadence_combo, self.mapping_section, self.mapping_toggle):
            control.setEnabled(True)
        self.import_button.setEnabled(bool(self._summary and self._summary.accepted_rows and not self._summary.conflicts and self.result is None))
        if self._closing:
            super().reject()

    def start_import(self):
        if self._thread is None and self._summary and self.import_button.isEnabled():
            self._start("import", session_id=self._summary.session_id)

    def reject(self):
        if self._thread is not None:
            self._closing = True
            self._cancel.set()
            self.cancel_button.setEnabled(False)
            self.status.setText("Cancelling safely; waiting for the background operation…")
        else:
            super().reject()

    def accept(self):
        if self._thread is None:
            super().accept()

    def closeEvent(self, event):
        if self._thread is not None:
            self.reject()
            event.ignore()
        else:
            event.accept()
