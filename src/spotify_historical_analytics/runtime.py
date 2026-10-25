from __future__ import annotations

import logging
import os
import sqlite3
import sys
import tempfile
from contextlib import closing
from logging.handlers import RotatingFileHandler
from pathlib import Path
from types import TracebackType

from PySide6.QtCore import QLockFile
from PySide6.QtWidgets import QApplication, QMessageBox

from .config import APP_ROOT, DB_PATH, LOG_PATH, ensure_user_directories

LOGGER = logging.getLogger("us_music_charts_analytics")


def configure_logging() -> None:
    ensure_user_directories()
    handler = RotatingFileHandler(
        LOG_PATH,
        maxBytes=2_000_000,
        backupCount=4,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
    )
    LOGGER.setLevel(logging.INFO)
    LOGGER.addHandler(handler)
    LOGGER.propagate = False
    logging.getLogger("PySide6").setLevel(logging.WARNING)


def legacy_database_candidates() -> tuple[Path, ...]:
    candidates = [
        Path.home() / ".spotify_historical_analytics" / "spotify_historical_analytics.db",
        Path.home() / "AppData" / "Local" / "SpotifyHistoricalAnalytics" / "spotify_historical_analytics.db",
    ]
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        candidates.insert(
            0,
            Path(local_app_data)
            / "SpotifyHistoricalAnalytics"
            / "spotify_historical_analytics.db",
        )
    return tuple(dict.fromkeys(candidate for candidate in candidates if candidate != DB_PATH))


def migrate_legacy_database(source: Path, destination: Path = DB_PATH) -> None:
    source = source.resolve()
    destination = destination.resolve()
    if source == destination:
        raise ValueError("The existing and new database paths are identical.")
    if not source.is_file():
        raise FileNotFoundError(f"The existing database was not found: {source}")
    if destination.exists():
        raise FileExistsError(f"The new database already exists and will not be overwritten: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    destination_reserved = False
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=f".{destination.name}.migration.",
            suffix=".tmp",
            delete=False,
        ) as temporary_file:
            temporary_path = Path(temporary_file.name)
        with closing(sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True)) as source_connection:
            with closing(sqlite3.connect(str(temporary_path))) as target_connection:
                source_connection.backup(target_connection)
                target_connection.commit()
                integrity = target_connection.execute("PRAGMA integrity_check").fetchone()[0]
                if integrity != "ok":
                    raise sqlite3.DatabaseError(f"Database integrity check failed: {integrity}")
        try:
            descriptor = os.open(destination, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            raise FileExistsError(
                f"The new database appeared during migration and will not be overwritten: {destination}"
            )
        os.close(descriptor)
        destination_reserved = True
        os.replace(temporary_path, destination)
        temporary_path = None
        destination_reserved = False
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        if destination_reserved:
            destination.unlink(missing_ok=True)


def acquire_instance_lock() -> QLockFile:
    lock = QLockFile(str(APP_ROOT / "config" / "application.lock"))
    lock.setStaleLockTime(0)
    if not lock.tryLock(0):
        raise RuntimeError("Another copy of the application is already running.")
    return lock


def handle_uncaught_exception(
    exception_type: type[BaseException],
    exception: BaseException,
    traceback: TracebackType | None,
) -> None:
    LOGGER.critical(
        "An unexpected application error occurred.",
        exc_info=(exception_type, exception, traceback),
    )
    app = QApplication.instance()
    if app is not None:
        QMessageBox.critical(
            None,
            "Application error",
            "The application encountered an unexpected error. "
            f"Details were saved to:\n{LOG_PATH}\n\n"
            "Restart the application. If the problem continues, include the log when contacting support.",
        )
    else:
        sys.__excepthook__(exception_type, exception, traceback)
