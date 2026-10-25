from __future__ import annotations

import os
import sys
from pathlib import Path

from . import __version__

APP_NAME = "US Music Charts Analytics"
APP_VERSION = __version__
APP_VENDOR = "US Music Charts Analytics"


def _application_root() -> Path:
    override = os.environ.get("SPOTIFY_ANALYTICS_DATA_DIR")
    if override:
        return Path(override).expanduser()
    local_app_data = os.environ.get("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "USMusicChartsAnalytics"
    if sys.platform.startswith("win"):
        return Path.home() / "AppData" / "Local" / "USMusicChartsAnalytics"
    data_home = os.environ.get("XDG_DATA_HOME")
    if data_home:
        return Path(data_home) / "us-music-charts-analytics"
    return Path.home() / ".local" / "share" / "us-music-charts-analytics"


APP_ROOT = _application_root()
DATABASE_DIR = APP_ROOT / "database"
LOG_DIR = APP_ROOT / "logs"
BACKUP_DIR = APP_ROOT / "backups"
EXPORT_DIR = APP_ROOT / "exports"
CONFIG_DIR = APP_ROOT / "config"
DB_PATH = DATABASE_DIR / "analytics.db"
LOG_PATH = LOG_DIR / "application.log"
SETTINGS_PATH = CONFIG_DIR / "settings.json"


def ensure_user_directories(root: Path | None = None) -> dict[str, Path]:
    base = root or APP_ROOT
    directories = {
        "root": base,
        "database": base / "database",
        "logs": base / "logs",
        "backups": base / "backups",
        "exports": base / "exports",
        "config": base / "config",
    }
    for directory in directories.values():
        directory.mkdir(parents=True, exist_ok=True)
    return directories
