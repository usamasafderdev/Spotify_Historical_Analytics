from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from .db import DatabaseManager
from .importer import _normalize_header, _parse_date


@dataclass
class MetadataImportResult:
    batch_id: str
    source_name: str
    total_rows: int
    imported_rows: int
    rejected_rows: int
    duplicates_skipped: int
    album_track_mappings: int
    artist_track_mappings: int
    rejected_details: list[str] = field(default_factory=list)


METADATA_FIELDS = {
    "track_id": ["trackid", "spotifytrackid", "spotifyid"],
    "album_id": ["albumid", "spotifyalbumid"],
    "album_name": ["albumname", "albumtitle", "album"],
    "album_artist": ["albumartist", "albumartists"],
    "track_name": ["trackname", "tracktitle", "title"],
    "artist_id": ["artistid", "spotifyartistid"],
    "artist_name": ["artistname", "artist"],
    "release_date": ["releasedate", "albumreleasedate"],
    "source_identifier": ["sourceidentifier", "sourceid", "datasetid"],
}

REQUIRED_FIELDS = ("track_id",)
SPOTIFY_ID_PATTERN = re.compile(r"^[A-Za-z0-9]{22}$")


def normalize_spotify_id(value: object) -> str:
    text = "" if value is None else str(value).strip()
    if not text:
        return ""
    if text.startswith("spotify:"):
        parts = text.split(":")
        return parts[-1].strip()
    if "open.spotify.com/" in text:
        return text.split("?", 1)[0].rstrip("/").rsplit("/", 1)[-1]
    return text


def is_valid_spotify_id(value: str) -> bool:
    return bool(SPOTIFY_ID_PATTERN.fullmatch(value))


def load_metadata_dataframe(path: str | Path) -> pd.DataFrame:
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(file_path, dtype=str, keep_default_na=False)
    if suffix == ".xlsx":
        return pd.read_excel(file_path, dtype=str, keep_default_na=False)
    raise ValueError("Metadata files must be CSV or XLSX.")


def load_metadata_preview(path: str | Path, rows: int = 12) -> pd.DataFrame:
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix == ".csv":
        return pd.read_csv(file_path, dtype=str, keep_default_na=False, nrows=rows)
    if suffix == ".xlsx":
        return pd.read_excel(file_path, dtype=str, keep_default_na=False, nrows=rows)
    raise ValueError("Metadata files must be CSV or XLSX.")


def suggest_metadata_columns(columns: list[str]) -> dict[str, str]:
    normalized = {_normalize_header(column): column for column in columns}
    return {
        field_name: next(
            (normalized[alias] for alias in aliases if alias in normalized),
            "",
        )
        for field_name, aliases in METADATA_FIELDS.items()
    }


def import_metadata_dataframe(
    db: DatabaseManager,
    dataframe: pd.DataFrame,
    source_name: str,
    source_license: str,
    file_name: str,
    column_mapping: dict[str, str],
) -> MetadataImportResult:
    missing = [
        field for field in REQUIRED_FIELDS
        if not column_mapping.get(field) or column_mapping[field] not in dataframe.columns
    ]
    if missing:
        raise ValueError(f"Metadata import requires mapped columns for: {', '.join(missing)}.")
    has_album_fields = bool(
        column_mapping.get("album_id")
        and column_mapping.get("album_name")
        and column_mapping["album_id"] in dataframe.columns
        and column_mapping["album_name"] in dataframe.columns
    )
    has_artist_id_field = bool(
        column_mapping.get("artist_id")
        and column_mapping["artist_id"] in dataframe.columns
    )
    if not has_album_fields and not has_artist_id_field:
        raise ValueError("Map album ID + album title, artist ID, or both, in addition to track ID.")

    batch_id = uuid.uuid4().hex
    total_rows = len(dataframe)
    imported_rows = rejected_rows = duplicates_skipped = 0
    album_track_mappings = artist_track_mappings = 0
    rejected_details: list[str] = []

    with db.transaction():
        db.connection.execute(
            "INSERT OR IGNORE INTO sources (name, license, remarks) VALUES (?, ?, ?)",
            (source_name, source_license, f"Metadata imported from {file_name}"),
        )
        db.connection.execute(
            """
            INSERT INTO metadata_import_batches (
                batch_id, file_name, source_name, source_license, total_rows
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (batch_id, file_name, source_name, source_license, total_rows),
        )

        for row_number, (_, row) in enumerate(dataframe.iterrows(), start=2):

            def value(field: str) -> str:
                column = column_mapping.get(field)
                if not column:
                    return ""
                item = row.get(column, "")
                return "" if pd.isna(item) else str(item).strip()

            track_id = normalize_spotify_id(value("track_id"))
            album_id = normalize_spotify_id(value("album_id"))
            album_name = value("album_name")
            album_artist = value("album_artist") or None
            track_name = value("track_name") or None
            artist_id = normalize_spotify_id(value("artist_id"))
            artist_name = value("artist_name") or None
            release_date = value("release_date") or None
            source_identifier = value("source_identifier") or None

            has_album_values = bool(album_id or album_name)
            valid_album_mapping = bool(album_id and album_name)
            reason = None
            if not track_id or not is_valid_spotify_id(track_id):
                reason = "missing or invalid Spotify track ID"
            elif has_album_values and not valid_album_mapping:
                reason = "album ID and album title must both be provided"
            elif valid_album_mapping and not is_valid_spotify_id(album_id):
                reason = "missing or invalid Spotify album ID"
            elif artist_id and not is_valid_spotify_id(artist_id):
                reason = "invalid Spotify artist ID"
            elif not valid_album_mapping and not artist_id:
                reason = "row must include an album mapping or artist ID"
            elif release_date:
                normalized_release_date = _parse_date(release_date)
                if normalized_release_date is None:
                    reason = "release date must use YYYY-MM-DD"
                else:
                    release_date = normalized_release_date

            if reason:
                rejected_rows += 1
                rejected_details.append(f"row {row_number}: {reason}")
                continue

            existing_album = (
                db.connection.execute(
                    "SELECT album_name, album_artist, release_date FROM albums WHERE album_id = ?",
                    (album_id,),
                ).fetchone()
                if valid_album_mapping
                else None
            )
            if existing_album:
                conflicts = [
                    (existing_album["album_name"], album_name),
                    (existing_album["album_artist"], album_artist),
                    (existing_album["release_date"], release_date),
                ]
                if any(old and new and old != new for old, new in conflicts):
                    rejected_rows += 1
                    rejected_details.append(
                        f"row {row_number}: conflicting metadata for existing album ID {album_id}"
                    )
                    continue
            if artist_id and artist_name:
                existing_artist = db.connection.execute(
                    "SELECT artist_name FROM artists WHERE artist_id = ?",
                    (artist_id,),
                ).fetchone()
                if existing_artist and existing_artist["artist_name"] and existing_artist["artist_name"] != artist_name:
                    rejected_rows += 1
                    rejected_details.append(
                        f"row {row_number}: conflicting metadata for existing artist ID {artist_id}"
                    )
                    continue

            existing_mapping = (
                db.connection.execute(
                    "SELECT 1 FROM track_albums WHERE track_id = ? AND album_id = ?",
                    (track_id, album_id),
                ).fetchone()
                if valid_album_mapping
                else None
            )
            if existing_mapping:
                duplicates_skipped += 1

            if valid_album_mapping:
                db.connection.execute(
                    """
                    INSERT INTO albums (
                        album_id, album_name, album_artist, release_date,
                        source_identifier, source_name, source_license, metadata_batch_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(album_id) DO UPDATE SET
                        album_name = COALESCE(albums.album_name, excluded.album_name),
                        album_artist = COALESCE(albums.album_artist, excluded.album_artist),
                        release_date = COALESCE(albums.release_date, excluded.release_date),
                        source_identifier = COALESCE(albums.source_identifier, excluded.source_identifier),
                        source_name = excluded.source_name,
                        source_license = excluded.source_license,
                        metadata_batch_id = excluded.metadata_batch_id
                    """,
                    (
                        album_id, album_name, album_artist, release_date,
                        source_identifier, source_name, source_license, batch_id,
                    ),
                )
                db.connection.execute(
                    """
                    INSERT INTO track_albums (
                        track_id, album_id, mapping_confidence, metadata_batch_id, mapping_status
                    ) VALUES (?, ?, 'stable-id', ?, 'id_match')
                    ON CONFLICT(track_id, album_id) DO UPDATE SET
                        mapping_confidence = 'stable-id',
                        metadata_batch_id = excluded.metadata_batch_id,
                        mapping_status = 'id_match'
                    """,
                    (track_id, album_id, batch_id),
                )
                album_track_mappings += int(not existing_mapping)

            if artist_id:
                db.connection.execute(
                    """
                    INSERT INTO artists (
                        artist_id, artist_name, source_name, source_license, metadata_batch_id
                    ) VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(artist_id) DO UPDATE SET
                        artist_name = COALESCE(excluded.artist_name, artists.artist_name),
                        source_name = excluded.source_name,
                        source_license = excluded.source_license,
                        metadata_batch_id = excluded.metadata_batch_id
                    """,
                    (artist_id, artist_name, source_name, source_license, batch_id),
                )
                existing_artist_mapping = db.connection.execute(
                    "SELECT 1 FROM track_artists WHERE track_id = ? AND artist_id = ?",
                    (track_id, artist_id),
                ).fetchone()
                db.connection.execute(
                    """
                    INSERT INTO track_artists (
                        track_id, artist_id, attribution_rule, is_primary,
                        metadata_batch_id, mapping_status
                    ) VALUES (?, ?, 'full-credit', 1, ?, 'id_match')
                    ON CONFLICT(track_id, artist_id, attribution_rule) DO UPDATE SET
                        metadata_batch_id = excluded.metadata_batch_id,
                        mapping_status = 'id_match'
                    """,
                    (track_id, artist_id, batch_id),
                )
                artist_track_mappings += int(not existing_artist_mapping)

            if track_name:
                db.connection.execute(
                    "UPDATE tracks SET track_name = ?, artist_names = COALESCE(?, artist_names) WHERE track_id = ?",
                    (track_name, artist_name, track_id),
                )
            imported_rows += 1

        db.connection.execute(
            """
            UPDATE metadata_import_batches
            SET imported_rows = ?, rejected_rows = ?, duplicates_skipped = ?
            WHERE batch_id = ?
            """,
            (imported_rows, rejected_rows, duplicates_skipped, batch_id),
        )

    return MetadataImportResult(
        batch_id=batch_id,
        source_name=source_name,
        total_rows=total_rows,
        imported_rows=imported_rows,
        rejected_rows=rejected_rows,
        duplicates_skipped=duplicates_skipped,
        album_track_mappings=album_track_mappings,
        artist_track_mappings=artist_track_mappings,
        rejected_details=rejected_details,
    )


def import_metadata_file(
    db: DatabaseManager,
    path: str | Path,
    source_name: str,
    source_license: str,
    column_mapping: dict[str, str] | None = None,
) -> MetadataImportResult:
    dataframe = load_metadata_dataframe(path)
    mapping = column_mapping or suggest_metadata_columns([str(column) for column in dataframe.columns])
    return import_metadata_dataframe(
        db,
        dataframe,
        source_name,
        source_license,
        Path(path).name,
        mapping,
    )
