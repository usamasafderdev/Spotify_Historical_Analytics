from __future__ import annotations

import sqlite3
import uuid
from datetime import date, timedelta
from pathlib import Path

from .config import DB_PATH


class DatabaseManager:
    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path is not None else DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(str(self.db_path))
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        self.initialize()

    def initialize(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                license TEXT,
                remarks TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS import_batches (
                batch_id TEXT PRIMARY KEY,
                source_name TEXT NOT NULL,
                source_license TEXT,
                chart_type TEXT NOT NULL,
                country TEXT NOT NULL,
                is_demo INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS chart_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                batch_id TEXT NOT NULL,
                source TEXT NOT NULL,
                source_license TEXT,
                chart_type TEXT NOT NULL,
                country TEXT NOT NULL,
                chart_date TEXT NOT NULL,
                weekly_start TEXT,
                weekly_end TEXT,
                position INTEGER,
                track_id TEXT,
                track_name TEXT NOT NULL,
                artist_names TEXT NOT NULL,
                streams INTEGER NOT NULL,
                original_url TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE (source, chart_type, country, chart_date, position, track_name, artist_names, streams)
            );

            CREATE TABLE IF NOT EXISTS tracks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_id TEXT NOT NULL UNIQUE,
                track_name TEXT,
                artist_names TEXT,
                source TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS artists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                artist_id TEXT NOT NULL UNIQUE,
                artist_name TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS albums (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                album_id TEXT NOT NULL UNIQUE,
                album_name TEXT,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE TABLE IF NOT EXISTS track_artists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_id TEXT NOT NULL,
                artist_id TEXT NOT NULL,
                attribution_rule TEXT DEFAULT 'primary-artist',
                is_primary INTEGER NOT NULL DEFAULT 1,
                UNIQUE (track_id, artist_id, attribution_rule)
            );

            CREATE TABLE IF NOT EXISTS track_albums (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                track_id TEXT NOT NULL,
                album_id TEXT NOT NULL,
                mapping_confidence TEXT DEFAULT 'unknown',
                UNIQUE (track_id, album_id)
            );

            CREATE INDEX IF NOT EXISTS idx_chart_records_date ON chart_records(chart_date, chart_type, country);
            CREATE INDEX IF NOT EXISTS idx_chart_records_source ON chart_records(source, chart_date);
            CREATE INDEX IF NOT EXISTS idx_chart_records_track ON chart_records(track_id, track_name);
            CREATE INDEX IF NOT EXISTS idx_chart_records_streams ON chart_records(streams);
            """
        )
        self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def ensure_source(self, source_name: str, license: str, remarks: str = "") -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO sources (name, license, remarks) VALUES (?, ?, ?)",
            (source_name, license, remarks),
        )
        self.connection.commit()

    def create_batch(self, source_name: str, source_license: str, chart_type: str, country: str, is_demo: bool = False) -> str:
        batch_id = uuid.uuid4().hex
        self.connection.execute(
            "INSERT INTO import_batches (batch_id, source_name, source_license, chart_type, country, is_demo) VALUES (?, ?, ?, ?, ?, ?)",
            (batch_id, source_name, source_license, chart_type, country, 1 if is_demo else 0),
        )
        self.connection.commit()
        return batch_id

    def register_chart_record(
        self,
        batch_id: str,
        source: str,
        source_license: str,
        chart_type: str,
        country: str,
        chart_date: str,
        weekly_start: str | None,
        weekly_end: str | None,
        position: int | None,
        track_id: str | None,
        track_name: str,
        artist_names: str,
        streams: int,
        original_url: str | None,
    ) -> None:
        self.connection.execute(
            """
            INSERT OR IGNORE INTO chart_records (
                batch_id, source, source_license, chart_type, country, chart_date, weekly_start, weekly_end,
                position, track_id, track_name, artist_names, streams, original_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                batch_id,
                source,
                source_license,
                chart_type,
                country,
                chart_date,
                weekly_start,
                weekly_end,
                position,
                track_id,
                track_name,
                artist_names,
                int(streams),
                original_url,
            ),
        )
        self.connection.commit()

    def upsert_track(self, track_id: str, track_name: str, artist_names: str, source: str) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO tracks (track_id, track_name, artist_names, source) VALUES (?, ?, ?, ?)",
            (track_id, track_name, artist_names, source),
        )
        self.connection.execute(
            "UPDATE tracks SET track_name = ?, artist_names = ?, source = ? WHERE track_id = ?",
            (track_name, artist_names, source, track_id),
        )
        self.connection.commit()

    def upsert_artist(self, artist_id: str, artist_name: str) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO artists (artist_id, artist_name) VALUES (?, ?)",
            (artist_id, artist_name),
        )
        self.connection.execute(
            "UPDATE artists SET artist_name = ? WHERE artist_id = ?",
            (artist_name, artist_id),
        )
        self.connection.commit()

    def upsert_album(self, album_id: str, album_name: str) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO albums (album_id, album_name) VALUES (?, ?)",
            (album_id, album_name),
        )
        self.connection.execute(
            "UPDATE albums SET album_name = ? WHERE album_id = ?",
            (album_name, album_id),
        )
        self.connection.commit()

    def get_summary(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        include_demo: bool = False,
        chart_type: str = "daily",
    ) -> dict:
        filters = ["country = 'US'", f"chart_type = '{chart_type}'"]
        if not include_demo:
            filters.append("source <> 'DEMO / SYNTHETIC'")
        if start_date:
            filters.append(f"chart_date >= '{start_date}'")
        if end_date:
            filters.append(f"chart_date <= '{end_date}'")
        where_clause = " AND ".join(filters)

        totals_sql = f"""
            SELECT
                COALESCE(SUM(streams), 0) AS total_streams,
                COUNT(DISTINCT CASE WHEN track_id IS NULL THEN track_name || '|' || artist_names ELSE track_id END) AS total_tracks,
                COUNT(DISTINCT artist_names) AS total_artists,
                COUNT(DISTINCT chart_date) AS chart_dates_with_data
            FROM chart_records
            WHERE {where_clause}
        """
        total_row = self.connection.execute(totals_sql).fetchone()

        if start_date and end_date:
            start_dt = date.fromisoformat(start_date)
            end_dt = date.fromisoformat(end_date)
            span_days = (end_dt - start_dt).days + 1
            coverage = 0.0 if span_days <= 0 else (int(total_row["chart_dates_with_data"]) / span_days) * 100.0
        else:
            coverage = 0.0

        return {
            "total_streams": int(total_row["total_streams"] or 0),
            "distinct_tracks": int(total_row["total_tracks"] or 0),
            "distinct_artists": int(total_row["total_artists"] or 0),
            "chart_dates_with_data": int(total_row["chart_dates_with_data"] or 0),
            "coverage_percentage": round(coverage, 2),
        }

    def get_top_tracks(
        self,
        limit: int = 10,
        start_date: str | None = None,
        end_date: str | None = None,
        include_demo: bool = False,
        chart_type: str = "daily",
    ) -> list[dict]:
        filters = ["country = 'US'", f"chart_type = '{chart_type}'"]
        if not include_demo:
            filters.append("source <> 'DEMO / SYNTHETIC'")
        if start_date:
            filters.append(f"chart_date >= '{start_date}'")
        if end_date:
            filters.append(f"chart_date <= '{end_date}'")
        where_clause = " AND ".join(filters)

        sql = f"""
            SELECT
                COALESCE(track_id, track_name || '|' || artist_names) AS track_key,
                track_name,
                artist_names,
                SUM(streams) AS total_streams,
                MIN(position) AS best_position,
                COUNT(DISTINCT chart_date) AS chart_appearances
            FROM chart_records
            WHERE {where_clause}
            GROUP BY track_key, track_name, artist_names
            ORDER BY total_streams DESC
            LIMIT {limit}
        """
        return [dict(row) for row in self.connection.execute(sql).fetchall()]

    def get_artist_summary(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        include_demo: bool = False,
        chart_type: str = "daily",
    ) -> list[dict]:
        filters = ["country = 'US'", f"chart_type = '{chart_type}'"]
        if not include_demo:
            filters.append("source <> 'DEMO / SYNTHETIC'")
        if start_date:
            filters.append(f"chart_date >= '{start_date}'")
        if end_date:
            filters.append(f"chart_date <= '{end_date}'")
        where_clause = " AND ".join(filters)

        sql = f"""
            SELECT
                artist_names AS artist_name,
                SUM(streams) AS charting_song_streams,
                COUNT(DISTINCT CASE WHEN track_id IS NULL THEN track_name || '|' || artist_names ELSE track_id END) AS track_count
            FROM chart_records
            WHERE {where_clause}
            GROUP BY artist_names
            ORDER BY charting_song_streams DESC
            LIMIT 20
        """
        return [dict(row) for row in self.connection.execute(sql).fetchall()]

    def get_coverage(self, chart_type: str = "daily") -> dict:
        dates_sql = f"SELECT DISTINCT chart_date FROM chart_records WHERE country = 'US' AND chart_type = '{chart_type}' ORDER BY chart_date"
        rows = self.connection.execute(dates_sql).fetchall()
        if not rows:
            return {"earliest": None, "latest": None, "missing_dates": []}
        coverage_dates = [row["chart_date"] for row in rows]
        earliest = coverage_dates[0]
        latest = coverage_dates[-1]
        missing = []
        start = date.fromisoformat(earliest)
        end = date.fromisoformat(latest)
        cursor = start
        while cursor <= end:
            iso = cursor.isoformat()
            if iso not in coverage_dates:
                missing.append(iso)
            cursor += timedelta(days=1)
        return {"earliest": earliest, "latest": latest, "missing_dates": missing}

    def backup_database(self, destination: str | Path) -> Path:
        target = Path(destination)
        target.parent.mkdir(parents=True, exist_ok=True)
        self.connection.backup(sqlite3.connect(str(target)))
        return target

    def restore_database(self, source_backup: str | Path) -> None:
        backup = Path(source_backup)
        if not backup.exists():
            raise FileNotFoundError(f"Backup file not found: {backup}")
        self.connection.close()
        self.db_path.unlink(missing_ok=True)
        sqlite3.connect(str(self.db_path)).close()
        self.connection = sqlite3.connect(str(self.db_path))
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        import shutil
        shutil.copy2(str(backup), str(self.db_path))
        self.connection = sqlite3.connect(str(self.db_path))
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")

    def seed_demo_dataset(self) -> str:
        batch_id = self.create_batch(
            source_name="DEMO / SYNTHETIC",
            source_license="Demo only. Not real Spotify chart data.",
            chart_type="daily",
            country="US",
            is_demo=True,
        )
        demo_rows = [
            (batch_id, "DEMO / SYNTHETIC", "Demo only. Not real Spotify chart data.", "daily", "US", "2024-01-01", None, None, 1, "demo_track_01", "Demo Song A", "Demo Artist One", 120000),
            (batch_id, "DEMO / SYNTHETIC", "Demo only. Not real Spotify chart data.", "daily", "US", "2024-01-01", None, None, 2, "demo_track_02", "Demo Song B", "Demo Artist One", 98000),
            (batch_id, "DEMO / SYNTHETIC", "Demo only. Not real Spotify chart data.", "daily", "US", "2024-01-02", None, None, 1, "demo_track_01", "Demo Song A", "Demo Artist One", 135000),
            (batch_id, "DEMO / SYNTHETIC", "Demo only. Not real Spotify chart data.", "daily", "US", "2024-01-03", None, None, 1, "demo_track_01", "Demo Song A", "Demo Artist One", 149000),
            (batch_id, "DEMO / SYNTHETIC", "Demo only. Not real Spotify chart data.", "daily", "US", "2024-01-03", None, None, 2, "demo_track_03", "Demo Song C", "Demo Artist Two", 89000),
        ]
        self.connection.executemany(
            """
            INSERT OR IGNORE INTO chart_records (
                batch_id, source, source_license, chart_type, country, chart_date, weekly_start, weekly_end,
                position, track_id, track_name, artist_names, streams, original_url
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [(*row[:13], None) for row in demo_rows],
        )
        self.connection.commit()
        return batch_id
