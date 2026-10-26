"""Shared dark surfaces, including top-level dialogs and native-style fallbacks."""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

DIALOG_STYLE = """
QDialog, QMessageBox, QProgressDialog,
QWidget#importContent, QScrollArea, QScrollArea > QWidget > QWidget {
    background-color:#141923; color:#F8FAFC;
}
QLabel, QCheckBox, QGroupBox { color:#F8FAFC; background:transparent; }
QWidget { font-family:'Segoe UI'; font-size:13px; }
QGroupBox { border:1px solid #475569; border-radius:6px; margin-top:14px; padding:18px 12px 12px; }
QGroupBox::title { subcontrol-origin:margin; left:12px; padding:0 5px; }
QLineEdit, QComboBox, QDateEdit, QTextEdit, QPlainTextEdit {
    color:#F8FAFC; background:#121823; border:1px solid #475569;
    border-radius:6px; padding:7px 9px; min-height:22px;
    selection-background-color:#6D28D9; selection-color:#FFFFFF;
}
QComboBox QAbstractItemView { background:#121823; color:#F8FAFC; selection-background-color:#6D28D9; selection-color:white; }
QPushButton { background:#1B2230; color:#F8FAFC; border:1px solid #475569; border-radius:6px; padding:8px 12px; min-height:20px; }
QPushButton#primary, QPushButton:default { background:#6D28D9; color:white; border-color:#A78BFA; font-weight:600; }
QPushButton:hover { background:#42316B; }
QPushButton:focus, QLineEdit:focus, QComboBox:focus { border:2px solid #C4B5FD; }
QPushButton#primary:disabled, QPushButton:default:disabled, QPushButton:disabled, QComboBox:disabled, QLineEdit:disabled { color:#A8B3C7; background:#202938; border-color:#475569; }
QProgressBar { background:#202938; color:#F8FAFC; border:1px solid #475569; border-radius:4px; text-align:center; min-height:12px; }
QProgressBar::chunk { background:#6D28D9; }
QScrollArea { border:0; }
QScrollBar:vertical { background:#202938; width:12px; }
QScrollBar::handle:vertical { background:#64748B; min-height:24px; border-radius:4px; }
QMessageBox QLabel { color:#F8FAFC; background:transparent; }
"""


def apply_dark_theme(app: QApplication) -> None:
    if app.property("darkThemeApplied"):
        return
    app.setStyle("Fusion")
    palette = QPalette()
    roles = {
        QPalette.Window: "#141923", QPalette.WindowText: "#F8FAFC",
        QPalette.Base: "#121823", QPalette.AlternateBase: "#202938",
        QPalette.Text: "#F8FAFC", QPalette.Button: "#1B2230",
        QPalette.ButtonText: "#F8FAFC", QPalette.Highlight: "#6D28D9",
        QPalette.HighlightedText: "#FFFFFF", QPalette.ToolTipBase: "#202938",
        QPalette.ToolTipText: "#F8FAFC", QPalette.PlaceholderText: "#A8B3C7",
    }
    for role, color in roles.items():
        palette.setColor(role, QColor(color))
    for role in (QPalette.Text, QPalette.ButtonText, QPalette.WindowText):
        palette.setColor(QPalette.Disabled, role, QColor("#A8B3C7"))
    app.setPalette(palette)
    app.setStyleSheet(DIALOG_STYLE)
    app.setAttribute(Qt.AA_DontUseNativeDialogs)
    app.setProperty("darkThemeApplied", True)
