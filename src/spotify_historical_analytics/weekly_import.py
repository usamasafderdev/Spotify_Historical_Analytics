from __future__ import annotations

from pathlib import Path
import re
import tempfile
from typing import Callable

from .db import DatabaseManager
from .import_sessions import ImportSessionStore


def import_weekly_files(
    db: DatabaseManager,
    paths: list[str | Path],
    progress: Callable[[str], None] | None = None,
) -> list[dict]:
    results = []
    with tempfile.TemporaryDirectory(prefix="chart-weekly-") as temporary:
        store = ImportSessionStore(Path(temporary) / "staging.db")
        try:
            for file_path in paths:
                path = Path(file_path)
                if progress:
                    progress(f"Validating weekly chart: {path.name}")
                try:
                    session = store.create_session(
                        path, "User weekly charts", "User-supplied weekly observations; source terms apply.", "weekly"
                    )
                    inspection = store.inspect_file(session)
                    mapping = inspection["schema"]
                    if not mapping.get("track_id") and not mapping.get("url"):
                        raise ValueError("Weekly imports require a Spotify track ID or track URL column.")
                    summary = store.prepare(session)
                    if summary.rejected_rows:
                        raise ValueError(f"File rejected: {summary.rejected_rows} invalid rows ({summary.rejection_counts}).")
                    invalid_ids = store.connection.execute(
                        "SELECT track_id FROM staged_chart_rows WHERE session_id=?", (session,)
                    )
                    if any(not re.fullmatch(r"[A-Za-z0-9]{22}", row[0]) for row in invalid_ids):
                        raise ValueError("Weekly imports require valid 22-character Spotify track IDs.")
                    result = store.finalize(session, db)
                    results.append({"file": path.name, "status": "Imported", **result})
                except Exception as error:
                    results.append({"file": path.name, "status": "Failed", "error": str(error)})
                finally:
                    with store.connection:
                        store.connection.execute("DELETE FROM staged_chart_rows")
        finally:
            store.close()
    return results
