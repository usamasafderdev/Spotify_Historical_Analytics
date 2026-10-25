from __future__ import annotations

import re
import sqlite3
import os
import tempfile
import uuid
from contextlib import contextmanager
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path
from typing import Iterator

from .config import DB_PATH


class DatabaseManager:
    @staticmethod
    def normalize_country(value: str | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        if not text:
            return None
        normalized = re.sub(r"[^a-z]", "", text.lower())
        country_map = {
            "us": "US",
            "usa": "US",
            "unitedstates": "US",
            "unitedstatesofamerica": "US",
            "u": "US",
        }
        return country_map.get(normalized, text.strip())

    @staticmethod
    def normalize_chart_type(value: str | None) -> str | None:
        if value is None:
            return None
        text = str(value).strip().lower()
        if not text:
            return None
        aliases = {
            "top200": "top200",
            "top_200": "top200",
            "viral": "viral",
            "daily": "daily",
            "weekly": "weekly",
        }
        return aliases.get(text, text)

    @staticmethod
    def validate_date_range(start_date: str | None, end_date: str | None) -> None:
        if start_date is not None:
            date.fromisoformat(start_date)
        if end_date is not None:
            date.fromisoformat(end_date)
        if start_date is None or end_date is None:
            return
        if start_date > end_date:
            raise ValueError("start_date must be on or before end_date")

    def __init__(self, db_path: str | Path | None = None) -> None:
        self.db_path = Path(db_path) if db_path is not None else DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._transaction_depth = 0
        self.connection = sqlite3.connect(str(self.db_path))
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")
        try:
            self.initialize()
        except Exception:
            self.connection.close()
            raise

    def initialize(self) -> None:
        schema_version = int(self.connection.execute("PRAGMA user_version").fetchone()[0])
        if schema_version > 1:
            raise RuntimeError(
                f"Database schema version {schema_version} is newer than this application supports (1)."
            )
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

            CREATE TABLE IF NOT EXISTS metadata_import_batches (
                batch_id TEXT PRIMARY KEY,
                file_name TEXT NOT NULL,
                source_name TEXT NOT NULL,
                source_license TEXT NOT NULL,
                total_rows INTEGER NOT NULL DEFAULT 0,
                imported_rows INTEGER NOT NULL DEFAULT 0,
                rejected_rows INTEGER NOT NULL DEFAULT 0,
                duplicates_skipped INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_chart_records_date ON chart_records(chart_date, chart_type, country);
            CREATE INDEX IF NOT EXISTS idx_chart_records_source ON chart_records(source, chart_date);
            CREATE INDEX IF NOT EXISTS idx_chart_records_track ON chart_records(track_id, track_name);
            CREATE INDEX IF NOT EXISTS idx_chart_records_streams ON chart_records(streams);
            CREATE INDEX IF NOT EXISTS idx_chart_records_market_type_date ON chart_records(country, chart_type, chart_date);
            CREATE INDEX IF NOT EXISTS idx_chart_records_filter_source ON chart_records(country, chart_type, source, chart_date);
            CREATE INDEX IF NOT EXISTS idx_chart_records_artist ON chart_records(country, chart_type, artist_names, chart_date);
            """
        )
        self._add_missing_columns(
            "artists",
            {
                "source_name": "TEXT",
                "source_license": "TEXT",
                "metadata_batch_id": "TEXT",
            },
        )
        self._add_missing_columns(
            "albums",
            {
                "album_artist": "TEXT",
                "release_date": "TEXT",
                "source_identifier": "TEXT",
                "source_name": "TEXT",
                "source_license": "TEXT",
                "metadata_batch_id": "TEXT",
            },
        )
        self._add_missing_columns(
            "track_artists",
            {
                "metadata_batch_id": "TEXT",
                "mapping_status": "TEXT NOT NULL DEFAULT 'legacy'",
            },
        )
        self._add_missing_columns(
            "track_albums",
            {
                "metadata_batch_id": "TEXT",
                "mapping_status": "TEXT NOT NULL DEFAULT 'unresolved'",
            },
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_track_artists_track_status ON track_artists(track_id, mapping_status, artist_id)"
        )
        self.connection.execute(
            "CREATE INDEX IF NOT EXISTS idx_track_albums_album_status ON track_albums(album_id, mapping_status, track_id)"
        )
        self.connection.execute("PRAGMA user_version = 1")
        self.connection.commit()

    def _add_missing_columns(self, table_name: str, columns: dict[str, str]) -> None:
        existing = {
            row["name"]
            for row in self.connection.execute(f"PRAGMA table_info({table_name})").fetchall()
        }
        for column_name, declaration in columns.items():
            if column_name not in existing:
                self.connection.execute(
                    f"ALTER TABLE {table_name} ADD COLUMN {column_name} {declaration}"
                )

    @contextmanager
    def transaction(self) -> Iterator[None]:
        outermost = self._transaction_depth == 0
        if outermost:
            self.connection.execute("BEGIN IMMEDIATE")
        self._transaction_depth += 1
        try:
            yield
        except Exception:
            self._transaction_depth -= 1
            self.connection.rollback()
            if not outermost:
                self._transaction_depth = 0
            raise
        else:
            self._transaction_depth -= 1
            if outermost:
                self.connection.commit()

    def _commit(self) -> None:
        if self._transaction_depth == 0:
            self.connection.commit()

    def close(self) -> None:
        self.connection.close()

    def ensure_source(self, source_name: str, license: str, remarks: str = "") -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO sources (name, license, remarks) VALUES (?, ?, ?)",
            (source_name, license, remarks),
        )
        self._commit()

    def create_batch(self, source_name: str, source_license: str, chart_type: str, country: str, is_demo: bool = False) -> str:
        batch_id = uuid.uuid4().hex
        self.connection.execute(
            "INSERT INTO import_batches (batch_id, source_name, source_license, chart_type, country, is_demo) VALUES (?, ?, ?, ?, ?, ?)",
            (batch_id, source_name, source_license, chart_type, country, 1 if is_demo else 0),
        )
        self._commit()
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
        self._commit()

    def upsert_track(self, track_id: str, track_name: str, artist_names: str, source: str) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO tracks (track_id, track_name, artist_names, source) VALUES (?, ?, ?, ?)",
            (track_id, track_name, artist_names, source),
        )
        self.connection.execute(
            "UPDATE tracks SET track_name = ?, artist_names = ?, source = ? WHERE track_id = ?",
            (track_name, artist_names, source, track_id),
        )
        self._commit()

    def upsert_artist(self, artist_id: str, artist_name: str) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO artists (artist_id, artist_name) VALUES (?, ?)",
            (artist_id, artist_name),
        )
        self.connection.execute(
            "UPDATE artists SET artist_name = ? WHERE artist_id = ?",
            (artist_name, artist_id),
        )
        self._commit()

    def upsert_album(self, album_id: str, album_name: str) -> None:
        self.connection.execute(
            "INSERT OR IGNORE INTO albums (album_id, album_name) VALUES (?, ?)",
            (album_id, album_name),
        )
        self.connection.execute(
            "UPDATE albums SET album_name = ? WHERE album_id = ?",
            (album_name, album_id),
        )
        self._commit()

    def get_summary(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        include_demo: bool = False,
        chart_type: str = "daily",
    ) -> dict:
        self.validate_date_range(start_date, end_date)
        chart_type = self.normalize_chart_type(chart_type) or "daily"

        filters = ["country = ?", "chart_type = ?"]
        params: list[str | int] = ["US", chart_type]
        if not include_demo:
            filters.append("source <> ?")
            params.append("DEMO / SYNTHETIC")
        if start_date:
            filters.append("chart_date >= ?")
            params.append(start_date)
        if end_date:
            filters.append("chart_date <= ?")
            params.append(end_date)
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
        total_row = self.connection.execute(totals_sql, params).fetchone()

        bounds = self.connection.execute(
            f"SELECT MIN(chart_date) AS earliest, MAX(chart_date) AS latest FROM chart_records WHERE {where_clause}",
            params,
        ).fetchone()
        range_start = start_date or (bounds["earliest"] if bounds else None)
        range_end = end_date or (bounds["latest"] if bounds else None)
        coverage = 0.0
        if range_start and range_end:
            start_dt = date.fromisoformat(range_start)
            end_dt = date.fromisoformat(range_end)
            span = (end_dt - start_dt).days
            expected_intervals = span // 7 + 1 if chart_type == "weekly" else span + 1
            coverage = (
                int(total_row["chart_dates_with_data"]) / expected_intervals * 100.0
                if expected_intervals > 0
                else 0.0
            )

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
        search: str | None = None,
    ) -> list[dict]:
        self.validate_date_range(start_date, end_date)
        chart_type = self.normalize_chart_type(chart_type) or "daily"

        filters = ["country = ?", "chart_type = ?"]
        params: list[str | int] = ["US", chart_type]
        if not include_demo:
            filters.append("source <> ?")
            params.append("DEMO / SYNTHETIC")
        if start_date:
            filters.append("chart_date >= ?")
            params.append(start_date)
        if end_date:
            filters.append("chart_date <= ?")
            params.append(end_date)
        if search:
            filters.append("(track_name LIKE ? COLLATE NOCASE OR artist_names LIKE ? COLLATE NOCASE)")
            params.extend([f"%{search}%", f"%{search}%"])
        where_clause = " AND ".join(filters)

        sql = f"""
            SELECT
                COALESCE(track_id, track_name || '|' || artist_names) AS track_key,
                MIN(track_name) AS track_name,
                MIN(artist_names) AS artist_names,
                SUM(streams) AS total_streams,
                MIN(position) AS best_position,
                COUNT(DISTINCT chart_date) AS chart_appearances
            FROM chart_records
            WHERE {where_clause}
            GROUP BY track_key
            ORDER BY total_streams DESC, track_name ASC, artist_names ASC
            LIMIT ?
        """
        params.append(limit)
        return [dict(row) for row in self.connection.execute(sql, params).fetchall()]

    def get_artist_summary(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        include_demo: bool = False,
        chart_type: str = "daily",
        limit: int = 20,
        search: str | None = None,
    ) -> list[dict]:
        self.validate_date_range(start_date, end_date)
        chart_type = self.normalize_chart_type(chart_type) or "daily"

        filters = ["c.country = ?", "c.chart_type = ?"]
        params: list[str | int] = ["US", chart_type]
        if not include_demo:
            filters.append("c.source <> ?")
            params.append("DEMO / SYNTHETIC")
        if start_date:
            filters.append("c.chart_date >= ?")
            params.append(start_date)
        if end_date:
            filters.append("c.chart_date <= ?")
            params.append(end_date)
        where_clause = " AND ".join(filters)

        sql = f"""
            WITH artist_observations AS (
                SELECT
                    'id:' || a.artist_id AS artist_key,
                    a.artist_id AS artist_id,
                    COALESCE(a.artist_name, '[Unlabeled artist ID]') AS artist_name,
                    SUM(c.streams) AS charting_song_streams,
                    COUNT(DISTINCT COALESCE(c.track_id, c.track_name || '|' || c.artist_names)) AS track_count,
                    COUNT(DISTINCT c.id) AS chart_appearances,
                    MIN(c.position) AS best_position,
                    MIN(c.chart_date) AS first_appearance,
                    MAX(c.chart_date) AS latest_appearance,
                    'Full-credit by supplied artist ID' AS attribution
                FROM chart_records c
                JOIN (
                    SELECT DISTINCT track_id, artist_id
                    FROM track_artists WHERE mapping_status = 'id_match'
                ) ta
                  ON ta.track_id = COALESCE(c.track_id, c.track_name || '|' || c.artist_names)
                JOIN artists a ON a.artist_id = ta.artist_id
                WHERE {where_clause}
                GROUP BY a.artist_id, a.artist_name
                UNION ALL
                SELECT
                    'credit:' || c.artist_names AS artist_key,
                    NULL AS artist_id,
                    c.artist_names AS artist_name,
                    SUM(c.streams) AS charting_song_streams,
                    COUNT(DISTINCT COALESCE(c.track_id, c.track_name || '|' || c.artist_names)) AS track_count,
                    COUNT(DISTINCT c.id) AS chart_appearances,
                    MIN(c.position) AS best_position,
                    MIN(c.chart_date) AS first_appearance,
                    MAX(c.chart_date) AS latest_appearance,
                    'Unresolved credited string; not split' AS attribution
                FROM chart_records c
                WHERE {where_clause}
                  AND NOT EXISTS (
                      SELECT 1 FROM track_artists ta
                      WHERE ta.track_id = COALESCE(c.track_id, c.track_name || '|' || c.artist_names)
                        AND ta.mapping_status = 'id_match'
                  )
                GROUP BY c.artist_names
            )
            SELECT * FROM artist_observations
            WHERE (? IS NULL OR artist_name LIKE ? COLLATE NOCASE OR artist_id LIKE ? COLLATE NOCASE)
            ORDER BY charting_song_streams DESC, artist_name ASC, artist_key ASC
            LIMIT ?
        """
        query_params = [*params, *params, search, f"%{search}%" if search else "", f"%{search}%" if search else "", limit]
        return [dict(row) for row in self.connection.execute(sql, query_params).fetchall()]

    def get_artist_detail(
        self,
        artist_key: str,
        start_date: str | None = None,
        end_date: str | None = None,
        chart_type: str = "daily",
        include_demo: bool = False,
    ) -> dict | None:
        self.validate_date_range(start_date, end_date)
        chart_type = self.normalize_chart_type(chart_type) or "daily"
        filters = ["c.country = ?", "c.chart_type = ?"]
        params: list[str | int] = ["US", chart_type]
        if not include_demo:
            filters.append("c.source <> ?")
            params.append("DEMO / SYNTHETIC")
        if start_date:
            filters.append("c.chart_date >= ?")
            params.append(start_date)
        if end_date:
            filters.append("c.chart_date <= ?")
            params.append(end_date)
        where_clause = " AND ".join(filters)
        if artist_key.startswith("id:"):
            artist_id = artist_key[3:]
            row = self.connection.execute(
                f"""
                    SELECT 'id:' || a.artist_id AS artist_key, a.artist_id,
                           COALESCE(a.artist_name, '[Unlabeled artist ID]') AS artist_name,
                           SUM(c.streams) AS charting_song_streams,
                           COUNT(DISTINCT COALESCE(c.track_id, c.track_name || '|' || c.artist_names)) AS track_count,
                           COUNT(DISTINCT c.id) AS chart_appearances,
                           MIN(c.position) AS best_position,
                           MIN(c.chart_date) AS first_appearance,
                           MAX(c.chart_date) AS latest_appearance,
                           'Full-credit by supplied artist ID' AS attribution
                    FROM chart_records c
                    JOIN (
                        SELECT DISTINCT track_id, artist_id
                        FROM track_artists WHERE mapping_status = 'id_match'
                    ) ta ON ta.track_id = COALESCE(c.track_id, c.track_name || '|' || c.artist_names)
                    JOIN artists a ON a.artist_id = ta.artist_id
                    WHERE {where_clause} AND a.artist_id = ?
                    GROUP BY a.artist_id, a.artist_name
                """,
                [*params, artist_id],
            ).fetchone()
            return dict(row) if row else None
        if artist_key.startswith("credit:"):
            artist_name = artist_key[7:]
            row = self.connection.execute(
                f"""
                    SELECT 'credit:' || c.artist_names AS artist_key,
                           NULL AS artist_id, c.artist_names AS artist_name,
                           SUM(c.streams) AS charting_song_streams,
                           COUNT(DISTINCT COALESCE(c.track_id, c.track_name || '|' || c.artist_names)) AS track_count,
                           COUNT(DISTINCT c.id) AS chart_appearances,
                           MIN(c.position) AS best_position,
                           MIN(c.chart_date) AS first_appearance,
                           MAX(c.chart_date) AS latest_appearance,
                           'Unresolved credited string; not split' AS attribution
                    FROM chart_records c
                    WHERE {where_clause} AND c.artist_names = ?
                      AND NOT EXISTS (
                          SELECT 1 FROM track_artists ta
                          WHERE ta.track_id = COALESCE(c.track_id, c.track_name || '|' || c.artist_names)
                            AND ta.mapping_status = 'id_match'
                      )
                    GROUP BY c.artist_names
                """,
                [*params, artist_name],
            ).fetchone()
            return dict(row) if row else None
        return None

    def get_artist_streams_over_time(
        self,
        artist_key: str,
        start_date: str | None = None,
        end_date: str | None = None,
        chart_type: str = "daily",
        include_demo: bool = False,
    ) -> list[dict]:
        self.validate_date_range(start_date, end_date)
        chart_type = self.normalize_chart_type(chart_type) or "daily"
        filters = ["c.country = ?", "c.chart_type = ?"]
        params: list[str | int] = ["US", chart_type]
        if not include_demo:
            filters.append("c.source <> ?")
            params.append("DEMO / SYNTHETIC")
        if start_date:
            filters.append("c.chart_date >= ?")
            params.append(start_date)
        if end_date:
            filters.append("c.chart_date <= ?")
            params.append(end_date)
        identity_filter = (
            "EXISTS (SELECT 1 FROM track_artists ta WHERE ta.track_id = "
            "COALESCE(c.track_id, c.track_name || '|' || c.artist_names) "
            "AND ta.artist_id = ? AND ta.mapping_status = 'id_match')"
            if artist_key.startswith("id:")
            else "c.artist_names = ? AND NOT EXISTS (SELECT 1 FROM track_artists ta WHERE ta.track_id = "
            "COALESCE(c.track_id, c.track_name || '|' || c.artist_names) AND ta.mapping_status = 'id_match')"
        )
        params.append(artist_key[3:] if artist_key.startswith("id:") else artist_key[7:])
        rows = self.connection.execute(
            f"""
                SELECT c.chart_date, SUM(c.streams) AS streams,
                       COUNT(DISTINCT c.id) AS chart_appearances
                FROM chart_records c
                WHERE {" AND ".join(filters)} AND {identity_filter}
                GROUP BY c.chart_date ORDER BY c.chart_date
            """,
            params,
        ).fetchall()
        return [dict(row) for row in rows]

    def get_album_rankings(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        chart_type: str = "daily",
        limit: int = 50,
        search: str | None = None,
        include_demo: bool = False,
    ) -> list[dict]:
        self.validate_date_range(start_date, end_date)
        chart_type = self.normalize_chart_type(chart_type) or "daily"
        filters = ["c.country = ?", "c.chart_type = ?", "ta.mapping_status = 'id_match'"]
        params: list[str | int] = ["US", chart_type]
        if not include_demo:
            filters.append("c.source <> ?")
            params.append("DEMO / SYNTHETIC")
        if start_date:
            filters.append("c.chart_date >= ?")
            params.append(start_date)
        if end_date:
            filters.append("c.chart_date <= ?")
            params.append(end_date)
        if search:
            filters.append("(al.album_name LIKE ? COLLATE NOCASE OR al.album_artist LIKE ? COLLATE NOCASE OR al.album_id LIKE ?)")
            params.extend([f"%{search}%"] * 3)
        rows = self.connection.execute(
            f"""
                SELECT al.album_id, al.album_name,
                       COALESCE(al.album_artist, '') AS album_artist,
                       SUM(c.streams) AS charting_track_streams,
                       COUNT(DISTINCT c.track_id) AS mapped_track_count,
                       COUNT(DISTINCT c.id) AS chart_appearances,
                       MIN(c.position) AS best_position,
                       MIN(c.chart_date) AS first_appearance,
                       MAX(c.chart_date) AS latest_appearance
                FROM chart_records c
                JOIN track_albums ta ON ta.track_id = c.track_id
                JOIN albums al ON al.album_id = ta.album_id
                WHERE {" AND ".join(filters)}
                GROUP BY al.album_id, al.album_name, al.album_artist
                ORDER BY charting_track_streams DESC, al.album_name COLLATE NOCASE, al.album_id
                LIMIT ?
            """,
            [*params, limit],
        ).fetchall()
        return [dict(row) for row in rows]

    def get_album_detail(
        self,
        album_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
        chart_type: str = "daily",
        include_demo: bool = False,
    ) -> dict | None:
        self.validate_date_range(start_date, end_date)
        chart_type = self.normalize_chart_type(chart_type) or "daily"
        filters = [
            "c.country = ?", "c.chart_type = ?",
            "ta.album_id = ?", "ta.mapping_status = 'id_match'",
        ]
        params: list[str | int] = ["US", chart_type, album_id]
        if not include_demo:
            filters.insert(2, "c.source <> ?")
            params.insert(2, "DEMO / SYNTHETIC")
        if start_date:
            filters.append("c.chart_date >= ?")
            params.append(start_date)
        if end_date:
            filters.append("c.chart_date <= ?")
            params.append(end_date)
        result = self.connection.execute(
            f"""
                SELECT al.album_id, al.album_name, al.album_artist, al.release_date,
                       SUM(c.streams) AS charting_track_streams,
                       COUNT(DISTINCT c.track_id) AS mapped_track_count,
                       COUNT(DISTINCT c.id) AS chart_appearances,
                       MIN(c.position) AS best_position,
                       MIN(c.chart_date) AS first_appearance,
                       MAX(c.chart_date) AS latest_appearance
                FROM chart_records c
                JOIN track_albums ta ON ta.track_id = c.track_id
                JOIN albums al ON al.album_id = ta.album_id
                WHERE {" AND ".join(filters)}
                GROUP BY al.album_id, al.album_name, al.album_artist, al.release_date
            """,
            params,
        ).fetchone()
        return dict(result) if result else None

    def get_album_tracks(
        self,
        album_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
        chart_type: str = "daily",
        include_demo: bool = False,
    ) -> list[dict]:
        self.validate_date_range(start_date, end_date)
        chart_type = self.normalize_chart_type(chart_type) or "daily"
        filters = [
            "c.country = ?", "c.chart_type = ?",
            "ta.album_id = ?", "ta.mapping_status = 'id_match'",
        ]
        params: list[str | int] = ["US", chart_type, album_id]
        if not include_demo:
            filters.insert(2, "c.source <> ?")
            params.insert(2, "DEMO / SYNTHETIC")
        if start_date:
            filters.append("c.chart_date >= ?")
            params.append(start_date)
        if end_date:
            filters.append("c.chart_date <= ?")
            params.append(end_date)
        rows = self.connection.execute(
            f"""
                SELECT c.track_id, MIN(c.track_name) AS track_name,
                       MIN(c.artist_names) AS artist_names,
                       SUM(c.streams) AS charting_track_streams,
                       COUNT(DISTINCT c.id) AS chart_appearances,
                       MIN(c.position) AS best_position
                FROM chart_records c
                JOIN track_albums ta ON ta.track_id = c.track_id
                WHERE {" AND ".join(filters)}
                GROUP BY c.track_id
                ORDER BY charting_track_streams DESC, track_name COLLATE NOCASE, c.track_id
            """,
            params,
        ).fetchall()
        return [dict(row) for row in rows]

    def get_album_streams_over_time(
        self,
        album_id: str,
        start_date: str | None = None,
        end_date: str | None = None,
        chart_type: str = "daily",
        include_demo: bool = False,
    ) -> list[dict]:
        self.validate_date_range(start_date, end_date)
        chart_type = self.normalize_chart_type(chart_type) or "daily"
        filters = [
            "c.country = ?", "c.chart_type = ?",
            "ta.album_id = ?", "ta.mapping_status = 'id_match'",
        ]
        params: list[str | int] = ["US", chart_type, album_id]
        if not include_demo:
            filters.insert(2, "c.source <> ?")
            params.insert(2, "DEMO / SYNTHETIC")
        if start_date:
            filters.append("c.chart_date >= ?")
            params.append(start_date)
        if end_date:
            filters.append("c.chart_date <= ?")
            params.append(end_date)
        rows = self.connection.execute(
            f"""
                SELECT c.chart_date, SUM(c.streams) AS streams,
                       COUNT(DISTINCT c.id) AS chart_appearances
                FROM chart_records c
                JOIN track_albums ta ON ta.track_id = c.track_id
                WHERE {" AND ".join(filters)}
                GROUP BY c.chart_date ORDER BY c.chart_date
            """,
            params,
        ).fetchall()
        return [dict(row) for row in rows]

    def get_metadata_mapping_summary(self) -> dict:
        row = self.connection.execute(
            """
                SELECT
                    (SELECT COUNT(DISTINCT track_id || '|' || artist_id)
                     FROM track_artists WHERE mapping_status = 'id_match') AS artist_track_mappings,
                    (SELECT COUNT(DISTINCT track_id || '|' || album_id)
                     FROM track_albums WHERE mapping_status = 'id_match') AS album_track_mappings,
                    (SELECT COUNT(DISTINCT track_id) FROM chart_records
                     WHERE track_id IS NOT NULL AND source <> 'DEMO / SYNTHETIC') AS chart_track_ids,
                    (SELECT COUNT(DISTINCT c.track_id) FROM chart_records c
                     WHERE c.track_id IS NOT NULL AND c.source <> 'DEMO / SYNTHETIC'
                       AND NOT EXISTS (
                           SELECT 1 FROM track_albums ta
                           WHERE ta.track_id = c.track_id AND ta.mapping_status = 'id_match'
                       )) AS unmapped_chart_track_ids
            """
        ).fetchone()
        return {
            **dict(row),
        }

    def get_coverage(self, chart_type: str = "daily", include_demo: bool = False) -> dict:
        chart_type = self.normalize_chart_type(chart_type) or "daily"
        source_filter = "" if include_demo else " AND source <> ?"
        params: tuple[str, ...] = ("US", chart_type) if include_demo else ("US", chart_type, "DEMO / SYNTHETIC")
        dates_sql = (
            "SELECT DISTINCT chart_date FROM chart_records WHERE country = ? AND chart_type = ?"
            + source_filter
            + " ORDER BY chart_date"
        )
        rows = self.connection.execute(dates_sql, params).fetchall()
        if not rows:
            return {"earliest": None, "latest": None, "missing_dates": []}
        coverage_dates = [row["chart_date"] for row in rows]
        earliest = coverage_dates[0]
        latest = coverage_dates[-1]
        missing = []
        start = date.fromisoformat(earliest)
        end = date.fromisoformat(latest)
        cursor = start
        interval = timedelta(days=7 if chart_type == "weekly" else 1)
        while cursor <= end:
            iso = cursor.isoformat()
            if iso not in coverage_dates:
                missing.append(iso)
            cursor += interval
        return {"earliest": earliest, "latest": latest, "missing_dates": missing}

    def get_available_date_bounds(
        self,
        include_demo: bool = False,
        chart_type: str = "daily",
    ) -> dict:
        self.validate_date_range(None, None)
        chart_type = self.normalize_chart_type(chart_type) or "daily"
        filters = ["country = ?", "chart_type = ?"]
        params: list[str] = ["US", chart_type]
        if not include_demo:
            filters.append("source <> ?")
            params.append("DEMO / SYNTHETIC")
        where_clause = " AND ".join(filters)
        row = self.connection.execute(
            f"SELECT MIN(chart_date) AS earliest, MAX(chart_date) AS latest FROM chart_records WHERE {where_clause}",
            params,
        ).fetchone()
        return {
            "earliest": row["earliest"] if row and row["earliest"] else None,
            "latest": row["latest"] if row and row["latest"] else None,
        }

    def get_streams_over_time(
        self,
        start_date: str | None = None,
        end_date: str | None = None,
        chart_type: str = "daily",
        track_key: str | None = None,
        include_demo: bool = False,
    ) -> list[dict]:
        self.validate_date_range(start_date, end_date)
        chart_type = self.normalize_chart_type(chart_type) or "daily"
        filters = ["country = ?", "chart_type = ?"]
        params: list[str | int] = ["US", chart_type]
        if not include_demo:
            filters.append("source <> ?")
            params.append("DEMO / SYNTHETIC")
        if start_date:
            filters.append("chart_date >= ?")
            params.append(start_date)
        if end_date:
            filters.append("chart_date <= ?")
            params.append(end_date)
        if track_key:
            filters.append("COALESCE(track_id, track_name || '|' || artist_names) = ?")
            params.append(track_key)
        rows = self.connection.execute(
            f"""
                SELECT chart_date, MIN(weekly_start) AS weekly_start,
                       MAX(weekly_end) AS weekly_end, SUM(streams) AS streams
                FROM chart_records
                WHERE {" AND ".join(filters)}
                GROUP BY chart_date
                ORDER BY chart_date
            """,
            params,
        ).fetchall()
        return [dict(row) for row in rows]

    def get_data_inventory(self, include_demo: bool = False) -> dict:
        summary = self.connection.execute(
            """
                SELECT
                    COUNT(*) AS all_rows,
                    SUM(CASE WHEN source = 'DEMO / SYNTHETIC' THEN 1 ELSE 0 END) AS demo_rows,
                    SUM(CASE WHEN source <> 'DEMO / SYNTHETIC' THEN 1 ELSE 0 END) AS real_rows,
                    MIN(CASE WHEN source <> 'DEMO / SYNTHETIC' THEN chart_date END) AS earliest_real,
                    MAX(CASE WHEN source <> 'DEMO / SYNTHETIC' THEN chart_date END) AS latest_real
                FROM chart_records
            """
        ).fetchone()
        source_rows = self.connection.execute(
            """
                SELECT source, source_license, chart_type, country,
                       COUNT(*) AS row_count, MIN(chart_date) AS earliest,
                       MAX(chart_date) AS latest,
                       MAX(CASE WHEN source = 'DEMO / SYNTHETIC' THEN 1 ELSE 0 END) AS is_demo
                FROM chart_records
                GROUP BY source, source_license, chart_type, country
                ORDER BY source, chart_type, country
            """
        ).fetchall()
        year_source_filter = "" if include_demo else " AND source <> 'DEMO / SYNTHETIC'"
        year_rows = self.connection.execute(
            f"""
                SELECT substr(chart_date, 1, 4) AS year, chart_type,
                       COUNT(DISTINCT chart_date) AS dates_with_data,
                       COUNT(*) AS row_count
                FROM chart_records
                WHERE country = 'US'{year_source_filter}
                GROUP BY year, chart_type
                ORDER BY year, chart_type
            """
        ).fetchall()
        metadata_rows = self.connection.execute(
            """
                SELECT batch_id, file_name, source_name, source_license,
                       total_rows, imported_rows, rejected_rows, duplicates_skipped,
                       created_at
                FROM metadata_import_batches
                ORDER BY created_at DESC, batch_id
            """
        ).fetchall()
        return {
            "summary": dict(summary),
            "sources": [dict(row) for row in source_rows],
            "years": [dict(row) for row in year_rows],
            "metadata_imports": [dict(row) for row in metadata_rows],
        }

    def get_chart_type_availability(self, include_demo: bool = False) -> list[str]:
        filters = ["country = ?"]
        params: list[str] = ["US"]
        if not include_demo:
            filters.append("source <> ?")
            params.append("DEMO / SYNTHETIC")
        where_clause = " AND ".join(filters)
        rows = self.connection.execute(
            f"SELECT DISTINCT chart_type FROM chart_records WHERE {where_clause} ORDER BY chart_type",
            params,
        ).fetchall()
        return [row["chart_type"] for row in rows]

    def get_song_detail(
        self,
        track_name: str,
        artist_names: str,
        start_date: str | None = None,
        end_date: str | None = None,
        include_demo: bool = False,
        chart_type: str = "daily",
        track_key: str | None = None,
    ) -> dict | None:
        self.validate_date_range(start_date, end_date)
        chart_type = self.normalize_chart_type(chart_type) or "daily"
        filters = ["country = ?", "chart_type = ?"]
        params: list[str | int] = ["US", chart_type]
        if track_key:
            filters.append("COALESCE(track_id, track_name || '|' || artist_names) = ?")
            params.append(track_key)
        else:
            filters.extend(["track_name = ?", "artist_names = ?"])
            params.extend([track_name, artist_names])
        if not include_demo:
            filters.append("source <> ?")
            params.append("DEMO / SYNTHETIC")
        if start_date:
            filters.append("chart_date >= ?")
            params.append(start_date)
        if end_date:
            filters.append("chart_date <= ?")
            params.append(end_date)
        where_clause = " AND ".join(filters)
        row = self.connection.execute(
            f"""
                SELECT
                    COALESCE(track_id, track_name || '|' || artist_names) AS track_key,
                    MIN(track_name) AS track_name,
                    MIN(artist_names) AS artist_names,
                    SUM(streams) AS total_streams,
                    MIN(position) AS best_position,
                    MIN(chart_date) AS first_appearance,
                    MAX(chart_date) AS latest_appearance,
                    COUNT(DISTINCT chart_date) AS observed_dates
                FROM chart_records
                WHERE {where_clause}
                GROUP BY track_key
            """,
            params,
        ).fetchone()
        return dict(row) if row is not None else None

    def backup_database(self, destination: str | Path) -> Path:
        target = Path(destination)
        if target.resolve() == self.db_path.resolve():
            raise ValueError("The backup destination must be different from the active database.")
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            with target.open("xb"):
                pass
        except FileExistsError:
            raise FileExistsError(f"Backup destination already exists and was not overwritten: {target}")
        try:
            backup_connection = sqlite3.connect(str(target))
            try:
                self.connection.backup(backup_connection)
                backup_connection.commit()
            finally:
                backup_connection.close()
        except Exception:
            target.unlink(missing_ok=True)
            raise
        return target

    def restore_database(self, source_backup: str | Path) -> None:
        backup = Path(source_backup).resolve()
        if not backup.exists():
            raise FileNotFoundError(f"Backup file not found: {backup}")
        if backup == self.db_path.resolve():
            raise ValueError("The restore source must be a backup, not the active database.")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        connection_closed = False
        try:
            with tempfile.NamedTemporaryFile(
                dir=self.db_path.parent,
                prefix=f".{self.db_path.name}.restore.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
            with closing(sqlite3.connect(f"{backup.as_uri()}?mode=ro", uri=True)) as backup_connection:
                with closing(sqlite3.connect(str(temporary_path))) as replacement_connection:
                    backup_connection.backup(replacement_connection)
                    replacement_connection.commit()
                    integrity = replacement_connection.execute("PRAGMA integrity_check").fetchone()[0]
                    if integrity != "ok":
                        raise sqlite3.DatabaseError(f"Backup integrity check failed: {integrity}")

            self.connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            self.connection.close()
            connection_closed = True
            os.replace(temporary_path, self.db_path)
            temporary_path = None
            self.db_path.with_name(f"{self.db_path.name}-wal").unlink(missing_ok=True)
            self.db_path.with_name(f"{self.db_path.name}-shm").unlink(missing_ok=True)
        except Exception:
            if connection_closed:
                self.connection = sqlite3.connect(str(self.db_path))
                self.connection.row_factory = sqlite3.Row
                self.connection.execute("PRAGMA foreign_keys = ON")
                self.connection.execute("PRAGMA journal_mode = WAL")
            raise
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)
        self.connection = sqlite3.connect(str(self.db_path))
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA foreign_keys = ON")
        self.connection.execute("PRAGMA journal_mode = WAL")

    def seed_demo_dataset(self) -> str:
        self.remove_demo_dataset()
        source = "DEMO / SYNTHETIC"
        source_license = "Generated fixture only. Not real Spotify data."
        artists = [
            (f"DEMOART{index:015d}", f"Demo Artist {index}")
            for index in range(1, 5)
        ]
        albums = [
            (f"DEMOALB{index:015d}", name, artist)
            for index, name, artist in [
                (1, "Demo Album North", "Demo Artist 1"),
                (2, "Demo Album South", "Demo Artist 2"),
                (3, "Demo Compilation", "Various demo artists"),
                (4, "Demo Compilation (Alternate Edition)", "Various demo artists"),
            ]
        ]
        tracks = [
            (f"demo_track_{index:02d}", f"Demo Song {index}", credited)
            for index, credited in [
                (1, "Demo Artist 1"),
                (2, "Demo Artist 1"),
                (3, "Demo Artist 2"),
                (4, "Demo Artist 3"),
                (5, "Demo Artist 1 & Demo Artist 2"),
                (6, "Demo Artist 4"),
            ]
        ]
        artist_by_track = {
            tracks[0][0]: [artists[0][0]],
            tracks[1][0]: [artists[0][0]],
            tracks[2][0]: [artists[1][0]],
            tracks[3][0]: [artists[2][0]],
            tracks[4][0]: [artists[0][0], artists[1][0]],
            tracks[5][0]: [artists[3][0]],
        }
        album_by_track = {
            tracks[0][0]: [albums[0][0]],
            tracks[1][0]: [albums[0][0]],
            tracks[2][0]: [albums[1][0]],
            tracks[3][0]: [albums[1][0]],
            tracks[4][0]: [albums[2][0], albums[3][0]],
        }
        license_note = "DEMO / SYNTHETIC — generated values for UI testing only."
        chart_rows: list[tuple[object, ...]] = []
        batch_ids: dict[str, str] = {}
        with self.transaction():
            self.ensure_source(source, source_license, "Isolated generated demo fixture.")
            for chart_type in ("daily", "weekly"):
                batch_ids[chart_type] = self.create_batch(
                    source, source_license, chart_type, "US", is_demo=True
                )

            for artist_id, artist_name in artists:
                self.connection.execute(
                    """
                    INSERT INTO artists (
                        artist_id, artist_name, source_name, source_license, metadata_batch_id
                    ) VALUES (?, ?, ?, ?, ?)
                    """,
                    (artist_id, artist_name, source, license_note, "synthetic-fixture"),
                )
            for album_id, album_name, album_artist in albums:
                self.connection.execute(
                    """
                    INSERT INTO albums (
                        album_id, album_name, album_artist, source_name, source_license,
                        metadata_batch_id
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (album_id, album_name, album_artist, source, license_note, "synthetic-fixture"),
                )
            for track_id, track_name, credited_artists in tracks:
                self.connection.execute(
                    "INSERT INTO tracks (track_id, track_name, artist_names, source) VALUES (?, ?, ?, ?)",
                    (track_id, track_name, credited_artists, source),
                )
                for artist_id in artist_by_track[track_id]:
                    self.connection.execute(
                        """
                        INSERT INTO track_artists (
                            track_id, artist_id, attribution_rule, is_primary,
                            metadata_batch_id, mapping_status
                        ) VALUES (?, ?, 'full-credit', 1, 'synthetic-fixture', 'id_match')
                        """,
                        (track_id, artist_id),
                    )
                for album_id in album_by_track.get(track_id, []):
                    self.connection.execute(
                        """
                        INSERT INTO track_albums (
                            track_id, album_id, mapping_confidence,
                            metadata_batch_id, mapping_status
                        ) VALUES (?, ?, 'synthetic-fixture', 'synthetic-fixture', 'id_match')
                        """,
                        (track_id, album_id),
                    )

            for year in range(2017, 2025):
                for month in range(1, 13):
                    if month == 4 and year % 2 == 0:
                        continue
                    chart_date = date(year, month, 1).isoformat()
                    self._append_demo_chart_day(
                        chart_rows, batch_ids["daily"], chart_date, tracks, source,
                        source_license, year, month,
                    )

            weekly_date = date(2017, 1, 2)
            final_week = date(2024, 12, 30)
            week_index = 0
            while weekly_date <= final_week:
                if week_index % 13 != 6:
                    self._append_demo_chart_day(
                        chart_rows, batch_ids["weekly"], weekly_date.isoformat(),
                        tracks, source, source_license, weekly_date.year, week_index,
                        chart_type="weekly",
                    )
                weekly_date += timedelta(days=7)
                week_index += 1

            self.connection.executemany(
                """
                INSERT INTO chart_records (
                    batch_id, source, source_license, chart_type, country, chart_date,
                    weekly_start, weekly_end, position, track_id, track_name,
                    artist_names, streams, original_url
                ) VALUES (?, ?, ?, ?, 'US', ?, ?, ?, ?, ?, ?, ?, ?, NULL)
                """,
                chart_rows,
            )
        return batch_ids["daily"]

    @staticmethod
    def _append_demo_chart_day(
        chart_rows: list[tuple[object, ...]],
        batch_id: str,
        chart_date: str,
        tracks: list[tuple[str, str, str]],
        source: str,
        source_license: str,
        year: int,
        period_index: int,
        chart_type: str = "daily",
    ) -> None:
        weekly_start = chart_date if chart_type == "weekly" else None
        weekly_end = chart_date if chart_type == "weekly" else None
        for position, (track_id, track_name, credited_artists) in enumerate(tracks, 1):
            streams = max(
                1000,
                250_000 - (position * 17_000) + ((year - 2017) * 2_300)
                + (period_index % 19) * 1_111,
            )
            chart_rows.append(
                (
                    batch_id, source, source_license, chart_type, chart_date,
                    weekly_start, weekly_end, position, track_id, track_name,
                    credited_artists, streams,
                )
            )

    def remove_demo_dataset(self) -> int:
        with self.transaction():
            row_count = int(
                self.connection.execute(
                    "SELECT COUNT(*) FROM chart_records WHERE source = 'DEMO / SYNTHETIC'"
                ).fetchone()[0]
            )
            demo_track_ids = [
                row[0]
                for row in self.connection.execute(
                    "SELECT track_id FROM tracks WHERE track_id LIKE 'demo_track_%'"
                ).fetchall()
            ]
            self.connection.execute(
                "DELETE FROM chart_records WHERE source = 'DEMO / SYNTHETIC'"
            )
            self.connection.execute(
                "DELETE FROM import_batches WHERE source_name = 'DEMO / SYNTHETIC'"
            )
            for track_id in demo_track_ids:
                self.connection.execute("DELETE FROM track_artists WHERE track_id = ?", (track_id,))
                self.connection.execute("DELETE FROM track_albums WHERE track_id = ?", (track_id,))
                self.connection.execute("DELETE FROM tracks WHERE track_id = ?", (track_id,))
            self.connection.execute("DELETE FROM artists WHERE artist_id LIKE 'DEMOART%'")
            self.connection.execute("DELETE FROM albums WHERE album_id LIKE 'DEMOALB%'")
        return row_count
