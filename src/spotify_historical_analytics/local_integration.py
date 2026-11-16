from __future__ import annotations

import argparse
from contextlib import contextmanager
import csv
from datetime import date, datetime, timedelta, timezone
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import sqlite3
import time
from urllib.parse import urlsplit

from .db import DatabaseManager
from .import_sessions import ImportSessionStore


SOURCE = "Owner-supplied local Spotify exports"
SOURCE_NOTE = "Local source files; original publisher/version not independently verified. No platform-wide totals inferred."
BATCH_SIZE = 2000
TEMP_LIMIT = 3 * 1024**3
METADATA_FILES = {"artists.csv": "artist", "albums.csv": "album", "songs.csv": "track",
                  "artwork.csv": "artwork", "links.csv": "links"}
WEEKLY_COLUMNS = {"cc", "week_end", "rank", "streams", "track_id", "title", "artists", "artist_uris"}


def spotify_id(value: str, kind: str) -> str | None:
    match = re.fullmatch(r"(?:spotify:" + kind + r":)?([A-Za-z0-9]{22})", value.strip())
    return match[1] if match else None


def artist_ids(value: str) -> list[str]:
    identifiers = [spotify_id(item.strip(), "artist") for item in value.split("|") if item.strip()]
    if any(identifier is None for identifier in identifiers):
        raise ValueError("Invalid supplied artist URI list")
    return list(dict.fromkeys(identifiers))


@contextmanager
def locked_source(path: Path):
    if path.suffix.lower() in {".part", ".crdownload", ".tmp"}:
        raise ValueError("Incomplete downloads are excluded")
    before = path.stat()
    if time.time() - before.st_mtime < 60:
        raise ValueError("File was recently modified; leave it for a later integration")
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        import msvcrt

        create_file = ctypes.WinDLL("kernel32", use_last_error=True).CreateFileW
        create_file.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                                wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE]
        create_file.restype = wintypes.HANDLE
        handle = create_file(str(path.resolve()), 0x80000000, 1, None, 3, 0x80, None)
        if handle == wintypes.HANDLE(-1).value:
            raise OSError(ctypes.get_last_error(), "Cannot obtain a read-only source handle excluding active writers", str(path))
        stream = os.fdopen(msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY), "rb")
    else:
        stream = path.open("rb")
    try:
        current = path.stat()
        if (current.st_size, current.st_mtime_ns) != (before.st_size, before.st_mtime_ns):
            raise ValueError("Source changed while opening")
        yield stream, before
        after = path.stat()
        if (after.st_size, after.st_mtime_ns) != (before.st_size, before.st_mtime_ns):
            raise ValueError("Source changed during import; transaction must roll back")
    finally:
        stream.close()


def initialize(db: DatabaseManager) -> None:
    db.connection.executescript("""
        CREATE TABLE IF NOT EXISTS integration_files (
            path TEXT PRIMARY KEY, size_bytes INTEGER, modified_ns INTEGER, sha256 TEXT,
            category TEXT, status TEXT, result_json TEXT, updated_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS entity_metadata (
            entity_type TEXT, entity_id TEXT, source_path TEXT, payload_json TEXT, payload_sha256 TEXT,
            PRIMARY KEY(entity_type, entity_id, source_path, payload_sha256)
        );
        CREATE TABLE IF NOT EXISTS entity_references (
            entity_type TEXT, entity_id TEXT, reference_type TEXT, url TEXT, source_path TEXT,
            PRIMARY KEY(entity_type, entity_id, reference_type, url)
        );
        CREATE TABLE IF NOT EXISTS album_artists (
            album_id TEXT, artist_id TEXT, source_path TEXT,
            PRIMARY KEY(album_id, artist_id)
        );
        CREATE INDEX IF NOT EXISTS idx_chart_records_identity
            ON chart_records(country, chart_type, chart_date, track_id);
        CREATE TEMP TABLE IF NOT EXISTS integration_metadata (
            entity_id TEXT, name TEXT, credits TEXT, release_date TEXT, payload TEXT, payload_sha256 TEXT
        );
        CREATE TEMP TABLE IF NOT EXISTS integration_artists (entity_id TEXT, artist_id TEXT);
        CREATE TEMP TABLE IF NOT EXISTS integration_references (
            entity_type TEXT, entity_id TEXT, reference_type TEXT, url TEXT
        );
        CREATE TEMP TABLE IF NOT EXISTS integration_chart (
            track_id TEXT, chart_date TEXT, weekly_start TEXT, weekly_end TEXT,
            position INTEGER, track_name TEXT, artist_names TEXT, streams INTEGER, conflict INTEGER DEFAULT 0
        );
        CREATE TEMP TABLE IF NOT EXISTS integration_album_chart (
            country TEXT, chart_date TEXT, weekly_start TEXT, weekly_end TEXT,
            position INTEGER, album_id TEXT, album_name TEXT, artist_names TEXT,
            conflict INTEGER DEFAULT 0
        );
        CREATE TEMP TABLE IF NOT EXISTS integration_artist_listeners (
            artist_id TEXT, metric_date TEXT, listeners INTEGER, conflict INTEGER DEFAULT 0
        );
    """)
    db.connection.execute("PRAGMA wal_autocheckpoint=2000")


def check_space(db: DatabaseManager) -> None:
    transient = sum(path.stat().st_size for path in db.db_path.parent.rglob("*")
                    if path.is_file() and path.name != db.db_path.name and path.suffix != ".json")
    if transient > TEMP_LIMIT or shutil.disk_usage(db.db_path.parent).free < 512 * 1024**2:
        raise RuntimeError("Integration stopped: temporary space exceeds 3 GiB or free disk is below 512 MiB")


def insert_count(connection, sql, parameters=()):
    before = connection.total_changes
    connection.execute(sql, parameters)
    return connection.total_changes - before


def flush_metadata(db, path, category, rows, relationships, references, result):
    connection = db.connection
    connection.execute("DELETE FROM integration_metadata")
    connection.execute("DELETE FROM integration_artists")
    connection.execute("DELETE FROM integration_references")
    connection.executemany("INSERT INTO integration_metadata VALUES (?,?,?,?,?,?)", rows)
    connection.executemany("INSERT INTO integration_artists VALUES (?,?)", relationships)
    connection.executemany("INSERT INTO integration_references VALUES (?,?,?,?)", references)
    if category in {"artist", "album", "track"}:
        table, key, label = {"artist": ("artists", "artist_id", "artist_name"),
                             "album": ("albums", "album_id", "album_name"),
                             "track": ("tracks", "track_id", "track_name")}[category]
        conflicts = connection.execute(
            f"SELECT incoming.entity_id FROM integration_metadata incoming JOIN {table} existing ON existing.{key}=incoming.entity_id WHERE existing.{label} IS NOT NULL AND existing.{label} != incoming.name"
        ).fetchall()
        result["conflicts"] += len(conflicts)
        for conflict in conflicts[:max(0, 8 - len(result["conflict_examples"]))]:
            result["conflict_examples"].append(conflict[0])
        connection.execute(
            f"DELETE FROM integration_metadata WHERE entity_id IN (SELECT incoming.entity_id FROM integration_metadata incoming JOIN {table} existing ON existing.{key}=incoming.entity_id WHERE existing.{label} IS NOT NULL AND existing.{label} != incoming.name)"
        )
        if category == "artist":
            added = insert_count(connection, "INSERT OR IGNORE INTO artists(artist_id,artist_name,source_name,source_license) SELECT entity_id,name,?,? FROM integration_metadata", (SOURCE, SOURCE_NOTE))
        elif category == "album":
            added = insert_count(connection, "INSERT OR IGNORE INTO albums(album_id,album_name,album_artist,release_date,source_name,source_license) SELECT entity_id,name,credits,release_date,?,? FROM integration_metadata", (SOURCE, SOURCE_NOTE))
        else:
            added = insert_count(connection, "INSERT OR IGNORE INTO tracks(track_id,track_name,artist_names,source) SELECT entity_id,name,credits,? FROM integration_metadata", (SOURCE,))
        result["entities_added"] += added
        connection.execute(f"UPDATE {table} SET {label}=(SELECT name FROM integration_metadata WHERE entity_id={table}.{key} LIMIT 1) WHERE {label} IS NULL AND {key} IN (SELECT entity_id FROM integration_metadata)")
        if category in {"track", "album"}:
            connection.execute("INSERT OR IGNORE INTO artists(artist_id, source_name, source_license) SELECT DISTINCT artist_id,?,? FROM integration_artists WHERE entity_id IN (SELECT entity_id FROM integration_metadata)", (SOURCE, SOURCE_NOTE))
            if category == "track":
                result["track_artist_links"] += insert_count(connection, "INSERT OR IGNORE INTO track_artists(track_id,artist_id,attribution_rule,mapping_status,metadata_batch_id) SELECT DISTINCT entity_id,artist_id,'full-credit','id_match',? FROM integration_artists WHERE entity_id IN (SELECT entity_id FROM integration_metadata)", (str(path),))
            else:
                result["album_artist_links"] += insert_count(connection, "INSERT OR IGNORE INTO album_artists SELECT DISTINCT entity_id,artist_id,? FROM integration_artists WHERE entity_id IN (SELECT entity_id FROM integration_metadata)", (str(path),))
    accepted = connection.execute("SELECT COUNT(*) FROM integration_metadata").fetchone()[0]
    added = insert_count(connection, "INSERT OR IGNORE INTO entity_metadata SELECT ?,entity_id,?,payload,payload_sha256 FROM integration_metadata", (category, str(path)))
    result["imported_rows"] += added
    result["duplicates"] += accepted - added
    result["references_added"] += insert_count(connection, "INSERT OR IGNORE INTO entity_references SELECT entity_type,entity_id,reference_type,url,? FROM integration_references WHERE entity_id IN (SELECT entity_id FROM integration_metadata)", (str(path),))
    check_space(db)


def import_metadata(db, path, category, reader, result):
    required = {
        "artist": {"artist_uri", "artist_name"}, "album": {"album_uri", "album_name"},
        "track": {"track_uri", "track_name", "artist_uris", "artist_names"},
        "artwork": {"uri", "type", "image_url"}, "links": {"spotify_uri", "type"},
    }[category]
    if not required.issubset(reader.fieldnames or []):
        raise ValueError("Metadata source schema is not recognized")
    rows, relationships, references = [], [], []
    for raw in reader:
        result["scanned_rows"] += 1
        try:
            kind = category if category in {"artist", "album", "track"} else {"song": "track", "artist": "artist", "album": "album"}[raw["type"]]
            identifier = spotify_id(raw.get(f"{kind}_uri", raw.get("uri", raw.get("spotify_uri", ""))), kind)
            if not identifier:
                raise ValueError("Invalid stable entity ID")
            name = raw.get(f"{kind}_name", "")
            if category in {"artist", "album", "track"} and not name.strip():
                raise ValueError("Missing entity name")
            supplied_artists = artist_ids(raw.get("artist_uris", ""))
            if category == "artwork":
                url = raw["image_url"]
                if urlsplit(url).scheme != "https" or not urlsplit(url).hostname:
                    raise ValueError("Invalid artwork URL")
                references.append((kind, identifier, "artwork", url))
            references.append((kind, identifier, "spotify", f"https://open.spotify.com/{kind}/{identifier}"))
            payload = json.dumps(raw, ensure_ascii=False, sort_keys=True)
            rows.append((identifier, name, raw.get("artist_names", ""), raw.get("release_date", ""), payload, hashlib.sha256(payload.encode("utf-8")).hexdigest()))
            relationships.extend((identifier, artist) for artist in supplied_artists)
        except (KeyError, ValueError):
            result["invalid_rows"] += 1
        if len(rows) >= BATCH_SIZE:
            flush_metadata(db, path, category, rows, relationships, references, result)
            rows, relationships, references = [], [], []
    if rows:
        flush_metadata(db, path, category, rows, relationships, references, result)


def flush_chart(db, batch, rows, relationships, result):
    connection = db.connection
    connection.execute("DELETE FROM integration_chart")
    connection.executemany("INSERT INTO integration_chart(track_id,chart_date,weekly_start,weekly_end,position,track_name,artist_names,streams) VALUES (?,?,?,?,?,?,?,?)", rows)
    connection.execute("""UPDATE integration_chart SET conflict=1 WHERE (track_id,chart_date) IN (
        SELECT track_id,chart_date FROM integration_chart GROUP BY track_id,chart_date
        HAVING COUNT(DISTINCT streams)>1 OR COUNT(DISTINCT position)>1 OR COUNT(DISTINCT track_name)>1 OR COUNT(DISTINCT artist_names)>1
    ) OR EXISTS (SELECT 1 FROM chart_records existing
        WHERE existing.country='US' AND existing.chart_type='weekly' AND existing.source <> 'DEMO / SYNTHETIC'
          AND existing.track_id=integration_chart.track_id AND existing.chart_date=integration_chart.chart_date
          AND (existing.streams != integration_chart.streams OR existing.position IS NOT integration_chart.position
               OR existing.track_name != integration_chart.track_name OR existing.artist_names != integration_chart.artist_names
               OR existing.weekly_start IS NOT integration_chart.weekly_start OR existing.weekly_end IS NOT integration_chart.weekly_end))""")
    conflicts = connection.execute("SELECT track_id,chart_date FROM integration_chart WHERE conflict=1").fetchall()
    result["conflicts"] += len(conflicts)
    for row in conflicts[:max(0, 8 - len(result["conflict_examples"]))]:
        result["conflict_examples"].append(f"{row[0]}@{row[1]}")
    added = insert_count(connection, """INSERT OR IGNORE INTO chart_records(
        batch_id,source,source_license,chart_type,country,chart_date,weekly_start,weekly_end,position,track_id,track_name,artist_names,streams)
        SELECT DISTINCT ?,?,?,'weekly','US',incoming.chart_date,incoming.weekly_start,incoming.weekly_end,
            incoming.position,incoming.track_id,incoming.track_name,incoming.artist_names,incoming.streams
        FROM integration_chart incoming WHERE conflict=0 AND NOT EXISTS (
            SELECT 1 FROM chart_records existing WHERE existing.country='US' AND existing.chart_type='weekly'
            AND existing.source <> 'DEMO / SYNTHETIC' AND existing.track_id=incoming.track_id AND existing.chart_date=incoming.chart_date
        )""", (batch, SOURCE, SOURCE_NOTE))
    result["imported_rows"] += added
    result["duplicates"] += len(rows) - len(conflicts) - added
    connection.execute("INSERT OR IGNORE INTO tracks(track_id,track_name,artist_names,source) SELECT track_id,MIN(track_name),MIN(artist_names),? FROM integration_chart WHERE conflict=0 GROUP BY track_id", (SOURCE,))
    connection.execute("DELETE FROM integration_artists")
    connection.executemany("INSERT INTO integration_artists VALUES (?,?)", relationships)
    connection.execute("INSERT OR IGNORE INTO artists(artist_id,source_name,source_license) SELECT DISTINCT artist_id,?,? FROM integration_artists WHERE entity_id IN (SELECT track_id FROM integration_chart WHERE conflict=0)", (SOURCE, SOURCE_NOTE))
    result["track_artist_links"] += insert_count(connection, "INSERT OR IGNORE INTO track_artists(track_id,artist_id,attribution_rule,mapping_status,metadata_batch_id) SELECT DISTINCT entity_id,artist_id,'full-credit','id_match',? FROM integration_artists WHERE entity_id IN (SELECT track_id FROM integration_chart WHERE conflict=0)", (batch,))
    check_space(db)


def flush_album_chart(db, batch, rows, result):
    connection = db.connection
    connection.execute("DELETE FROM integration_album_chart")
    connection.executemany(
        """INSERT INTO integration_album_chart(
               country,chart_date,weekly_start,weekly_end,position,album_id,album_name,artist_names
           ) VALUES (?,?,?,?,?,?,?,?)""",
        rows,
    )
    connection.execute("""UPDATE integration_album_chart SET conflict=1 WHERE (country,chart_date,album_id) IN (
        SELECT country,chart_date,album_id FROM integration_album_chart
        GROUP BY country,chart_date,album_id
        HAVING COUNT(DISTINCT position)>1 OR COUNT(DISTINCT album_name)>1 OR COUNT(DISTINCT artist_names)>1
    ) OR EXISTS (SELECT 1 FROM album_chart_records existing
        WHERE existing.country=integration_album_chart.country
          AND existing.chart_type='weekly'
          AND existing.chart_date=integration_album_chart.chart_date
          AND existing.album_id=integration_album_chart.album_id
          AND (existing.position != integration_album_chart.position
               OR existing.album_name != integration_album_chart.album_name
               OR existing.artist_names != integration_album_chart.artist_names
               OR existing.weekly_start != integration_album_chart.weekly_start
               OR existing.weekly_end != integration_album_chart.weekly_end))""")
    conflicts = connection.execute(
        "SELECT COUNT(*) FROM integration_album_chart WHERE conflict=1"
    ).fetchone()[0]
    result["conflicts"] += conflicts
    added = insert_count(connection, """INSERT OR IGNORE INTO album_chart_records(
        batch_id,source,source_license,chart_type,country,chart_date,weekly_start,weekly_end,
        position,album_id,album_name,artist_names)
        SELECT DISTINCT ?,?,?,'weekly',incoming.country,incoming.chart_date,incoming.weekly_start,
            incoming.weekly_end,incoming.position,incoming.album_id,incoming.album_name,incoming.artist_names
        FROM integration_album_chart incoming
        WHERE incoming.conflict=0 AND NOT EXISTS (
            SELECT 1 FROM album_chart_records existing
            WHERE existing.country=incoming.country AND existing.chart_type='weekly'
              AND existing.chart_date=incoming.chart_date AND existing.album_id=incoming.album_id
        )""", (batch, SOURCE, SOURCE_NOTE))
    result["imported_rows"] += added
    result["album_records_added"] += added
    result["duplicates"] += len(rows) - conflicts - added
    check_space(db)


def import_album_weekly(db, reader, result):
    required = {"date", "country", "rank", "uri", "album_name", "artist_names"}
    if not required.issubset(reader.fieldnames or []):
        raise ValueError("Weekly album source schema is not recognized")
    result["stream_column_present"] = "streams" in (reader.fieldnames or [])
    batch = db.create_batch(SOURCE, SOURCE_NOTE, "weekly_album", "US")
    rows = []
    album_ids = set()
    dates = set()
    for raw in reader:
        result["scanned_rows"] += 1
        if DatabaseManager.normalize_country(raw["country"]) != "US":
            result["excluded_non_us"] += 1
            continue
        try:
            chart_date = date.fromisoformat(raw["date"])
            album_id = spotify_id(raw["uri"], "album")
            position = int(raw["rank"])
            album_name = raw["album_name"].strip()
            if (chart_date.isoformat() != raw["date"] or chart_date.weekday() != 3
                    or not album_id or position < 1 or not album_name):
                raise ValueError("Invalid US album chart identity, date, or position")
            rows.append((
                "US", chart_date.isoformat(), (chart_date - timedelta(days=6)).isoformat(),
                chart_date.isoformat(), position, album_id, album_name, raw["artist_names"],
            ))
            album_ids.add(album_id)
            dates.add(chart_date.isoformat())
            result["earliest"] = min(result["earliest"] or chart_date.isoformat(), chart_date.isoformat())
            result["latest"] = max(result["latest"] or chart_date.isoformat(), chart_date.isoformat())
        except (KeyError, ValueError):
            result["invalid_rows"] += 1
        if len(rows) >= BATCH_SIZE:
            flush_album_chart(db, batch, rows, result)
            rows = []
    if rows:
        flush_album_chart(db, batch, rows, result)
    known_album_ids = {
        row[0] for row in db.connection.execute("SELECT album_id FROM albums")
    }
    result["unique_album_ids"] = len(album_ids)
    result["album_ids_matching_metadata"] = len(album_ids & known_album_ids)
    result["observed_dates"] = len(dates)


def flush_artist_listeners(db, rows, result):
    connection = db.connection
    connection.execute("DELETE FROM integration_artist_listeners")
    connection.executemany(
        "INSERT INTO integration_artist_listeners(artist_id,metric_date,listeners) VALUES (?,?,?)",
        rows,
    )
    connection.execute("""UPDATE integration_artist_listeners SET conflict=1 WHERE (artist_id,metric_date) IN (
        SELECT artist_id,metric_date FROM integration_artist_listeners
        GROUP BY artist_id,metric_date HAVING COUNT(DISTINCT listeners)>1
    ) OR EXISTS (SELECT 1 FROM artist_listener_records existing
        WHERE existing.artist_id=integration_artist_listeners.artist_id
          AND existing.metric_date=integration_artist_listeners.metric_date
          AND existing.listeners != integration_artist_listeners.listeners)""")
    conflicts = connection.execute(
        "SELECT COUNT(*) FROM integration_artist_listeners WHERE conflict=1"
    ).fetchone()[0]
    result["conflicts"] += conflicts
    added = insert_count(connection, """INSERT OR IGNORE INTO artist_listener_records(
        artist_id,metric_date,listeners,source,source_license)
        SELECT DISTINCT incoming.artist_id,incoming.metric_date,incoming.listeners,?,?
        FROM integration_artist_listeners incoming
        WHERE incoming.conflict=0 AND NOT EXISTS (
            SELECT 1 FROM artist_listener_records existing
            WHERE existing.artist_id=incoming.artist_id
              AND existing.metric_date=incoming.metric_date
        )""", (SOURCE, SOURCE_NOTE))
    result["imported_rows"] += added
    result["listener_records_added"] += added
    result["duplicates"] += len(rows) - conflicts - added
    check_space(db)


def import_artist_listener_metrics(db, reader, result):
    if not {"artist_id", "date", "listeners"}.issubset(reader.fieldnames or []):
        raise ValueError("Artist listener source schema is not recognized")
    rows = []
    artist_ids = set()
    dates = set()
    for raw in reader:
        result["scanned_rows"] += 1
        try:
            artist_id = spotify_id(raw["artist_id"], "artist")
            metric_date = date.fromisoformat(raw["date"])
            listeners = int(raw["listeners"])
            if (not artist_id or metric_date.isoformat() != raw["date"]
                    or listeners < 0 or listeners > 2**63 - 1):
                raise ValueError("Invalid artist listener identity, date, or count")
            rows.append((artist_id, metric_date.isoformat(), listeners))
            artist_ids.add(artist_id)
            dates.add(metric_date.isoformat())
            result["earliest"] = min(result["earliest"] or metric_date.isoformat(), metric_date.isoformat())
            result["latest"] = max(result["latest"] or metric_date.isoformat(), metric_date.isoformat())
        except (KeyError, ValueError):
            result["invalid_rows"] += 1
        if len(rows) >= BATCH_SIZE:
            flush_artist_listeners(db, rows, result)
            rows = []
    if rows:
        flush_artist_listeners(db, rows, result)
    known_artist_ids = {
        row[0] for row in db.connection.execute("SELECT artist_id FROM artists")
    }
    result["unique_artist_ids"] = len(artist_ids)
    result["artist_ids_matching_metadata"] = len(artist_ids & known_artist_ids)
    result["observed_dates"] = len(dates)


def import_weekly(db, reader, result):
    if not WEEKLY_COLUMNS.issubset(reader.fieldnames or []):
        raise ValueError("Weekly source schema is not recognized")
    batch = db.create_batch(SOURCE, SOURCE_NOTE, "weekly", "US")
    mapping = {"date": "week_end", "country": "cc", "position": "rank", "track_name": "title",
               "artist_names": "artists", "track_id": "track_id", "streams": "streams",
               "weekly_start": "_week_start", "weekly_end": "week_end"}
    rows, relationships = [], []
    for raw in reader:
        result["scanned_rows"] += 1
        if DatabaseManager.normalize_country(raw["cc"]) != "US":
            result["excluded_non_us"] += 1
            continue
        try:
            end = date.fromisoformat(raw["week_end"])
            raw["_week_start"] = (end - timedelta(days=6)).isoformat()
            record, reason = ImportSessionStore._normalize_row(raw, mapping, "weekly")
            if record is None or not spotify_id(record["track_id"], "track") or end.weekday() != 3 or not record["position"]:
                raise ValueError(reason or "Invalid weekly identity, position, or reporting end")
            supplied_artists = artist_ids(raw["artist_uris"])
            rows.append(tuple(record[key] for key in ("track_id", "chart_date", "weekly_start", "weekly_end", "position", "track_name", "artist_names", "streams")))
            relationships.extend((record["track_id"], artist) for artist in supplied_artists)
            result["earliest"] = min(result["earliest"] or record["chart_date"], record["chart_date"])
            result["latest"] = max(result["latest"] or record["chart_date"], record["chart_date"])
        except (KeyError, ValueError):
            result["invalid_rows"] += 1
        if len(rows) >= BATCH_SIZE:
            flush_chart(db, batch, rows, relationships, result)
            rows, relationships = [], []
    if rows:
        flush_chart(db, batch, rows, relationships, result)


def integrate_file(db: DatabaseManager, path: Path, category: str) -> dict:
    stat = path.stat()
    previous = db.connection.execute("SELECT * FROM integration_files WHERE path=?", (str(path.resolve()),)).fetchone()
    if previous and previous["status"] == "complete" and (previous["size_bytes"], previous["modified_ns"]) == (stat.st_size, stat.st_mtime_ns):
        return {"file": path.name, "status": "unchanged", **json.loads(previous["result_json"])}
    result = {"scanned_rows": 0, "imported_rows": 0, "duplicates": 0, "conflicts": 0,
              "invalid_rows": 0, "excluded_non_us": 0, "entities_added": 0, "references_added": 0,
              "track_artist_links": 0, "album_artist_links": 0, "earliest": None, "latest": None,
              "conflict_examples": []}
    if category == "album_weekly":
        result["album_records_added"] = 0
        result["stream_column_present"] = False
    elif category == "artist_listener_metrics":
        result["listener_records_added"] = 0
    with db.transaction():
        with locked_source(path) as (binary, initial):
            digest = hashlib.sha256()
            for block in iter(lambda: binary.read(1024 * 1024), b""):
                digest.update(block)
            binary.seek(0)
            decoded = gzip.GzipFile(fileobj=binary) if path.name.endswith(".gz") else binary
            text = io.TextIOWrapper(decoded, encoding="utf-8-sig", newline="")
            reader = csv.DictReader(text)
            db.ensure_source(SOURCE, SOURCE_NOTE)
            if category == "weekly":
                import_weekly(db, reader, result)
            elif category == "album_weekly":
                import_album_weekly(db, reader, result)
            elif category == "artist_listener_metrics":
                import_artist_listener_metrics(db, reader, result)
            else:
                import_metadata(db, path, category, reader, result)
            db.connection.execute("INSERT OR REPLACE INTO integration_files(path,size_bytes,modified_ns,sha256,category,status,result_json) VALUES (?,?,?,?,?,'complete',?)",
                                  (str(path.resolve()), initial.st_size, initial.st_mtime_ns, digest.hexdigest(), category, json.dumps(result)))
    db.connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
    return {"file": path.name, "status": "complete", **result}


def main() -> int:
    parser = argparse.ArgumentParser(description="Stream completed local metadata and US weekly exports into an isolated development database")
    parser.add_argument("--downloads", type=Path, required=True)
    parser.add_argument("--data-dir", type=Path, required=True)
    options = parser.parse_args()
    target = options.data_dir.resolve()
    target.mkdir(parents=True, exist_ok=True)
    db_path = target / "database" / "analytics.db"
    if db_path.exists():
        with sqlite3.connect(f"{db_path.as_uri()}?mode=ro", uri=True) as probe:
            if not probe.execute("SELECT 1 FROM sqlite_master WHERE name='integration_files'").fetchone():
                raise ValueError("Destination is an existing user database; choose a new integration directory")
    db = DatabaseManager(db_path)
    try:
        initialize(db)
        skipped = []
        candidates_to_import = []
        for filename, category in METADATA_FILES.items():
            candidates = [options.downloads / filename, options.downloads / filename.replace(".csv", "(1).csv")]
            path = next((candidate for candidate in candidates if candidate.is_file()), None)
            if path:
                candidates_to_import.append((path, category))
        for path in sorted(options.downloads.glob("spotify_top200_positions_*.csv.gz")):
            candidates_to_import.append((path, "weekly"))
        for filename, category in (
            ("charts_albums_weekly.csv", "album_weekly"),
            ("artist_listeners_daily.csv", "artist_listener_metrics"),
        ):
            path = options.downloads / filename
            if path.is_file():
                candidates_to_import.append((path, category))
        for path, category in candidates_to_import:
            try:
                print(json.dumps(integrate_file(db, path, category)), flush=True)
            except (ValueError, OSError) as error:
                if isinstance(error, OSError) and "active writers" not in str(error):
                    raise
                result = {"file": path.name, "status": "skipped", "reason": str(error)}
                skipped.append(result)
                print(json.dumps(result), flush=True)
        db.connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        manifest = [dict(row) for row in db.connection.execute("SELECT * FROM integration_files ORDER BY path")]
        report = {"database": str(db_path), "provenance": SOURCE_NOTE, "files": manifest,
                  "skipped_files": skipped,
                  "created_utc": datetime.now(timezone.utc).isoformat(),
                  "database_bytes": db_path.stat().st_size}
        (target / "source-manifest.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps({"database": str(db_path), "bytes": db_path.stat().st_size}), flush=True)
    finally:
        db.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
