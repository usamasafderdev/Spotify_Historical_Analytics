from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .config import SETTINGS_PATH

DEFAULT_SETTINGS: dict[str, Any] = {
    "last_import_directory": "",
    "last_export_directory": "",
    "last_backup_directory": "",
}


class SettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or SETTINGS_PATH
        self.values = dict(DEFAULT_SETTINGS)
        self.load_error: str | None = None
        if self.path.exists():
            try:
                stored = json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                self.load_error = f"Could not read application settings at {self.path}: {exc}"
            else:
                if not isinstance(stored, dict):
                    self.load_error = f"Application settings at {self.path} must contain a JSON object."
                else:
                    self.values.update(
                        {key: stored[key] for key in DEFAULT_SETTINGS if isinstance(stored.get(key, ""), str)}
                    )

    def get(self, key: str, default: str = "") -> str:
        value = self.values.get(key, default)
        return value if isinstance(value, str) else default

    def set(self, key: str, value: str) -> None:
        if key not in DEFAULT_SETTINGS:
            raise KeyError(f"Unknown application setting: {key}")
        self.values[key] = value
        self.save()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f".{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                json.dump(self.values, temporary_file, ensure_ascii=False, indent=2)
                temporary_file.write("\n")
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, self.path)
        except OSError as exc:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
            raise RuntimeError(f"Could not save application settings at {self.path}: {exc}") from exc
