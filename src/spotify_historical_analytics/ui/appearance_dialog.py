from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QHBoxLayout, QHeaderView, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout,
)

from ..services.appearances import chart_showings


class AppearanceDialog(QDialog):
    def __init__(self, db, category: str, filters: dict, search: str, limit: int,
                 hide_repeats: bool = False, include_demo: bool = False, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{category.title()} chart showings")
        self.resize(900, 560)
        self.db, self.category, self.filters = db, category, filters
        self.search, self.limit, self.include_demo = search, limit, include_demo
        layout = QVBoxLayout(self)
        note = QLabel(
            f"{category.title()} with known stable IDs only. One showing per entity and reporting date. "
            "Artist/album streams come from mapped charting tracks; position is their best track position. "
            "Rankings and full-history totals remain unchanged."
        )
        note.setWordWrap(True)
        layout.addWidget(note)
        controls = QHBoxLayout()
        self.hide_repeats = QCheckBox("Hide Repeats")
        self.hide_repeats.setChecked(hide_repeats)
        controls.addWidget(self.hide_repeats)
        controls.addWidget(QLabel("Sort"))
        self.sort = QComboBox()
        for label, value in [("Highest streams", "streams"), ("Best position", "position"),
                             ("Newest date", "newest"), ("Oldest date", "oldest")]:
            self.sort.addItem(label, value)
        controls.addWidget(self.sort)
        controls.addStretch()
        controls.addWidget(QLabel(f"Top {limit} after repeat filtering"))
        layout.addLayout(controls)
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["Entity", "Stable ID", "Reporting date", "Chart streams", "Position", "Appearances"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        layout.addWidget(self.table, 1)
        self.status = QLabel()
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.hide_repeats.toggled.connect(self.refresh)
        self.sort.currentIndexChanged.connect(self.refresh)
        self.refresh()

    def refresh(self):
        try:
            self.rows = chart_showings(
                self.db, self.category, **self.filters, search=self.search, limit=self.limit,
                hide_repeats=self.hide_repeats.isChecked(), sort=self.sort.currentData(),
                include_demo=self.include_demo,
            )
            self.table.setRowCount(len(self.rows))
            for index, row in enumerate(self.rows):
                count = row["chart_appearances"]
                values = [row["entity_name"], row["entity_id"], row["chart_date"],
                          f"{row['streams']:,}", row["position"] if row["position"] is not None else "Unavailable",
                          f"Repeat ({count})" if count > 1 else str(count)]
                for column, value in enumerate(values):
                    item = QTableWidgetItem(str(value))
                    item.setToolTip("Appearance counts use all eligible filtered dates before the list limit." if column == 5 else str(value))
                    self.table.setItem(index, column, item)
            self.status.setText(
                f"{len(self.rows)} showing(s). Counts use the complete eligible history. "
                + ("One best-sorted showing per entity." if self.hide_repeats.isChecked() else "Additional appearances are visible.")
                if self.rows else "No showings with stable IDs match the active filters."
            )
        except Exception as error:
            self.rows = []
            self.table.setRowCount(0)
            self.status.setText(f"Unable to load chart showings: {error}")
