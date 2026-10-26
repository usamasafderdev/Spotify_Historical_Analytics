from __future__ import annotations

import os
from pathlib import Path

os.environ["QT_QPA_PLATFORM"] = "offscreen"

import pytest
from PySide6.QtCore import QPoint
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication, QDialog, QLabel, QMessageBox, QVBoxLayout

from spotify_historical_analytics.ui.import_dialog import ImportDialog
from spotify_historical_analytics.ui.theme import apply_dark_theme


def contrast(first, second):
    def luminance(color):
        components = [color.redF(), color.greenF(), color.blueF()]
        linear = [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in components]
        return sum(v * weight for v, weight in zip(linear, (0.2126, 0.7152, 0.0722)))
    values = sorted([luminance(first), luminance(second)])
    return (values[1] + 0.05) / (values[0] + 0.05)


@pytest.fixture
def app():
    instance = QApplication.instance() or QApplication([])
    apply_dark_theme(instance)
    return instance


def assert_readable(widget, foreground=QPalette.WindowText, background=QPalette.Window):
    assert contrast(widget.palette().color(foreground), widget.palette().color(background)) >= 4.5


def test_dialog_and_message_box_render_dark_pixels(app):
    dialog = QDialog()
    layout = QVBoxLayout(dialog)
    label = QLabel("Readable warning text")
    layout.addWidget(label)
    dialog.show()
    message = QMessageBox(QMessageBox.Warning, "Warning", "Choose an existing CSV or XLSX file.")
    message.show()
    app.processEvents()
    for widget in (dialog, message):
        assert_readable(widget)
        snapshot = widget.grab().toImage()
        assert snapshot.pixelColor(2, 2).lightnessF() < 0.2
    assert_readable(label)
    for child in message.findChildren(QLabel):
        if child.text():
            assert_readable(child)
    for button in message.buttons():
        assert_readable(button, QPalette.ButtonText, QPalette.Button)
    dialog.close()
    message.close()


@pytest.mark.parametrize("size", [(864, 448), (960, 536), (960, 620), (960, 680), (720, 440)])
def test_import_dialog_contrast_scroll_and_actions(app, tmp_path: Path, size):
    dialog = ImportDialog(tmp_path / "production.db", tmp_path / "staging.db")
    dialog.resize(*size)
    dialog.show()
    app.processEvents()
    try:
        assert_readable(dialog)
        snapshot = dialog.grab().toImage()
        assert snapshot.pixelColor(snapshot.width() - 20, 10).lightnessF() < 0.2
        assert snapshot.pixelColor(10, snapshot.height() - 10).lightnessF() < 0.2
        for label in dialog.findChildren(QLabel):
            if label.text():
                assert_readable(label)
        for button in (dialog.import_button, dialog.cancel_button):
            assert dialog.rect().contains(button.mapTo(dialog, QPoint(0, 0)))
            assert dialog.rect().contains(button.mapTo(dialog, button.rect().bottomRight()))
            assert_readable(button, QPalette.ButtonText, QPalette.Button)
        dialog.mapping_section.show()
        dialog.mapping_toggle.setChecked(True)
        app.processEvents()
        assert dialog.scroll.horizontalScrollBar().maximum() == 0
        assert dialog.scroll.verticalScrollBar().maximum() > 0
        dialog.optional_mapping_toggle.setChecked(True)
        app.processEvents()
        for combo in dialog.mapping_combos.values():
            assert_readable(combo, QPalette.Text, QPalette.Base)
            assert combo.height() >= combo.fontMetrics().height() + 12
        boxes = [combo.geometry().translated(combo.parentWidget().mapTo(dialog, QPoint(0, 0)))
                 for combo in dialog.mapping_combos.values()]
        for position, box in enumerate(boxes):
            assert all(not box.intersects(other) for other in boxes[position + 1:])
    finally:
        dialog.close()


def test_primary_and_helper_colors_meet_aa():
    for foreground, background in [
        ("#FFFFFF", "#6D28D9"), ("#F8FAFC", "#141923"),
        ("#F8FAFC", "#121823"), ("#C4B5FD", "#141923"),
        ("#FDE68A", "#141923"), ("#34D399", "#141923"),
        ("#A8B3C7", "#202938"),
    ]:
        assert contrast(QColor(foreground), QColor(background)) >= 4.5
