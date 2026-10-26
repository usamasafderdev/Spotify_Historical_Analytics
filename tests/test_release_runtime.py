from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

from spotify_historical_analytics import __version__
from spotify_historical_analytics import config
from spotify_historical_analytics.resources import resource_path
from spotify_historical_analytics.settings import SettingsStore
from spotify_historical_analytics.runtime import (
    acquire_instance_lock,
    legacy_database_candidates,
    migrate_legacy_database,
)


def test_user_data_directories_are_created(tmp_path: Path) -> None:
    paths = config.ensure_user_directories(tmp_path / "USMusicChartsAnalytics")
    assert set(paths) == {"root", "database", "logs", "backups", "exports", "config"}
    assert all(path.is_dir() for path in paths.values())


def test_windows_user_data_root_and_override(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path / "Local AppData"))
    monkeypatch.delenv("SPOTIFY_ANALYTICS_DATA_DIR", raising=False)
    assert config._application_root() == tmp_path / "Local AppData" / "USMusicChartsAnalytics"

    override = tmp_path / "Custom Data"
    monkeypatch.setenv("SPOTIFY_ANALYTICS_DATA_DIR", str(override))
    assert config._application_root() == override


def test_frozen_app_data_root_uses_local_app_data_not_bundle(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    user_data = tmp_path / "Local AppData"
    bundle_data = tmp_path / "PyInstaller bundle"
    monkeypatch.setenv("LOCALAPPDATA", str(user_data))
    monkeypatch.delenv("SPOTIFY_ANALYTICS_DATA_DIR", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle_data), raising=False)

    assert config._application_root() == user_data / "USMusicChartsAnalytics"
    assert config._application_root() != bundle_data


def test_settings_persist_recent_paths_atomically(tmp_path: Path) -> None:
    settings_path = tmp_path / "config" / "settings.json"
    settings = SettingsStore(settings_path)
    assert settings.get("last_import_directory") == ""
    settings.set("last_import_directory", str(tmp_path / "Import folder"))
    settings.set("last_export_directory", str(tmp_path / "Export folder"))

    reloaded = SettingsStore(settings_path)
    assert reloaded.get("last_import_directory") == str(tmp_path / "Import folder")
    assert reloaded.get("last_export_directory") == str(tmp_path / "Export folder")
    assert list(settings_path.parent.glob("*.tmp")) == []


def test_corrupt_settings_report_recovery_and_use_default_directories(tmp_path: Path) -> None:
    settings_path = tmp_path / "settings.json"
    settings_path.write_text("{invalid", encoding="utf-8")
    settings = SettingsStore(settings_path)
    assert settings.load_error is not None
    assert "Could not read application settings" in settings.load_error
    assert settings.get("last_import_directory") == ""


def test_legacy_database_copy_is_explicit_and_never_overwrites(tmp_path: Path) -> None:
    source = tmp_path / "old database.sqlite"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE retained (value TEXT NOT NULL)")
        connection.execute("INSERT INTO retained VALUES ('preserved')")
    destination = tmp_path / "new" / "database.sqlite"

    migrate_legacy_database(source, destination)
    assert source.exists()
    with sqlite3.connect(destination) as connection:
        assert connection.execute("SELECT value FROM retained").fetchone()[0] == "preserved"
        assert connection.execute("PRAGMA integrity_check").fetchone()[0] == "ok"

    with pytest.raises(FileExistsError, match="will not be overwritten"):
        migrate_legacy_database(source, destination)
    with sqlite3.connect(destination) as connection:
        assert connection.execute("SELECT value FROM retained").fetchone()[0] == "preserved"


def test_invalid_legacy_database_does_not_create_destination(tmp_path: Path) -> None:
    source = tmp_path / "broken source.sqlite"
    source.write_text("not SQLite", encoding="utf-8")
    destination = tmp_path / "new" / "database.sqlite"

    with pytest.raises(sqlite3.DatabaseError):
        migrate_legacy_database(source, destination)

    assert not destination.exists()
    assert not list(destination.parent.glob("*.migration.*"))


def test_legacy_database_candidates_include_previous_home_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "home", classmethod(lambda _: tmp_path))
    monkeypatch.delenv("LOCALAPPDATA", raising=False)
    candidates = legacy_database_candidates()
    assert tmp_path / ".spotify_historical_analytics" / "spotify_historical_analytics.db" in candidates


def test_resource_path_supports_development_and_frozen_runtime(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    development_path = resource_path("assets/app_icon.svg")
    assert development_path.name == "app_icon.svg"
    assert development_path.exists()

    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path), raising=False)
    assert resource_path("assets/app_icon.ico") == tmp_path / "assets" / "app_icon.ico"


def test_single_instance_lock_rejects_second_writer(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr("spotify_historical_analytics.runtime.APP_ROOT", tmp_path)
    config.ensure_user_directories(tmp_path)
    first_lock = acquire_instance_lock()
    try:
        with pytest.raises(RuntimeError, match="already running"):
            acquire_instance_lock()
    finally:
        first_lock.unlock()


def test_application_identity_uses_central_version() -> None:
    assert config.APP_NAME == "US Music Charts Analytics"
    assert config.APP_VERSION == __version__
