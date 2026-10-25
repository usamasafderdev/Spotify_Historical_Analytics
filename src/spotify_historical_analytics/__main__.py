from __future__ import annotations

import sys

from PySide6.QtCore import QTimer
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from .config import APP_NAME, APP_VERSION, DB_PATH, LOG_PATH
from .resources import resource_path
from .runtime import (
    LOGGER,
    acquire_instance_lock,
    configure_logging,
    handle_uncaught_exception,
    legacy_database_candidates,
    migrate_legacy_database,
)


def main() -> int:
    if "--release-export-test" in sys.argv:
        from .release_checks import run_packaged_export_checks

        return run_packaged_export_checks()

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationDisplayName(APP_NAME)
    app.setOrganizationName("US Music Charts Analytics")
    app.setApplicationVersion(APP_VERSION)
    app.setWindowIcon(QIcon(str(resource_path("assets/app_icon.ico"))))
    try:
        configure_logging()
    except OSError:
        QMessageBox.critical(
            None,
            "User data folder unavailable",
            "The application could not create its local data and log folders. "
            "Check that your Windows user account can write to its Local AppData folder.",
        )
        return 1
    sys.excepthook = handle_uncaught_exception
    try:
        lock = acquire_instance_lock()
    except RuntimeError:
        QMessageBox.information(
            None,
            APP_NAME,
            "US Music Charts Analytics is already running.",
        )
        return 1

    try:
        smoke_test = "--smoke-test" in sys.argv
        if not smoke_test and not DB_PATH.exists():
            legacy_path = next(
                (path for path in legacy_database_candidates() if path.is_file()),
                None,
            )
            if legacy_path is not None:
                choice = QMessageBox.question(
                    None,
                    "Existing local database found",
                    "An existing development database was found at:\n"
                    f"{legacy_path}\n\n"
                    "Copy its records into the new per-user data folder?\n"
                    "The original database will not be moved or changed.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if choice == QMessageBox.StandardButton.Yes:
                    try:
                        migrate_legacy_database(legacy_path)
                    except Exception:
                        LOGGER.exception("Could not copy the existing local database.")
                        QMessageBox.critical(
                            None,
                            "Database copy failed",
                            "The existing database was not changed. "
                            f"Check the log for details:\n{LOG_PATH}",
                        )
                        return 1

        try:
            from .ui.main_window import MainWindow

            window = MainWindow()
        except Exception:
            LOGGER.exception("The application UI could not be initialized.")
            if not smoke_test:
                QMessageBox.critical(
                    None,
                    "Application could not start",
                    "The application could not initialize its dashboard. "
                    f"Review the local log for details:\n{LOG_PATH}",
                )
            return 1
        window.show()
        if smoke_test:
            QTimer.singleShot(5000, window.close)
        return app.exec()
    finally:
        lock.unlock()


if __name__ == "__main__":
    raise SystemExit(main())
