from __future__ import annotations

import sqlite3
from pathlib import Path

import pandas as pd
import pytest

from spotify_historical_analytics.db import DatabaseManager
from spotify_historical_analytics.metadata_importer import import_metadata_dataframe


TRACK_A = "A" * 22
TRACK_B = "B" * 22
TRACK_UNMAPPED = "C" * 22
ALBUM_ONE = "D" * 22
ALBUM_EDITION = "E" * 22
ARTIST_ONE = "F" * 22
ARTIST_TWO = "G" * 22


def register_observation(
    db: DatabaseManager,
    track_id: str,
    track_name: str,
    credited_artists: str,
    chart_date: str,
    position: int,
    streams: int,
) -> None:
    db.register_chart_record(
        batch_id="synthetic-phase3-fixture",
        source="Synthetic Phase 3 fixture",
        source_license="Synthetic test rows only",
        chart_type="daily",
        country="US",
        chart_date=chart_date,
        weekly_start=None,
        weekly_end=None,
        position=position,
        track_id=track_id,
        track_name=track_name,
        artist_names=credited_artists,
        streams=streams,
        original_url=None,
    )


def metadata_frame() -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Spotify Track ID": TRACK_A,
                "Spotify Album ID": ALBUM_ONE,
                "Album Title": "Studio Album",
                "Album Artist": "Primary Artist",
                "Track Title": "Mapped Track A",
                "Artist ID": ARTIST_ONE,
                "Artist Name": "Artist One",
                "Release Date": "2020-01-02",
                "Source Identifier": "authorized-catalog-v1",
            },
            {
                "Spotify Track ID": TRACK_A,
                "Spotify Album ID": ALBUM_ONE,
                "Album Title": "Studio Album",
                "Album Artist": "Primary Artist",
                "Track Title": "Mapped Track A",
                "Artist ID": ARTIST_TWO,
                "Artist Name": "Artist Two",
                "Release Date": "2020-01-02",
                "Source Identifier": "authorized-catalog-v1",
            },
            {
                "Spotify Track ID": TRACK_B,
                "Spotify Album ID": ALBUM_ONE,
                "Album Title": "Studio Album",
                "Album Artist": "Primary Artist",
                "Track Title": "Mapped Track B",
                "Artist ID": ARTIST_TWO,
                "Artist Name": "Artist Two",
                "Release Date": "2020-01-02",
                "Source Identifier": "authorized-catalog-v1",
            },
            {
                "Spotify Track ID": TRACK_A,
                "Spotify Album ID": ALBUM_EDITION,
                "Album Title": "Studio Album (Single Edition)",
                "Album Artist": "Primary Artist",
                "Track Title": "Mapped Track A",
                "Artist ID": ARTIST_ONE,
                "Artist Name": "Artist One",
                "Release Date": "2021-05-01",
                "Source Identifier": "authorized-catalog-v1",
            },
        ]
    )


MAPPING = {
    "track_id": "Spotify Track ID",
    "album_id": "Spotify Album ID",
    "album_name": "Album Title",
    "album_artist": "Album Artist",
    "track_name": "Track Title",
    "artist_id": "Artist ID",
    "artist_name": "Artist Name",
    "release_date": "Release Date",
    "source_identifier": "Source Identifier",
}


def test_artist_full_credit_album_mappings_and_date_filtering(tmp_path: Path) -> None:
    db = DatabaseManager(tmp_path / "phase3.db")
    register_observation(db, TRACK_A, "Mapped Track A", "Artist One, Artist Two", "2024-01-02", 1, 100)
    register_observation(db, TRACK_A, "Mapped Track A", "Artist One, Artist Two", "2024-01-03", 2, 50)
    register_observation(db, TRACK_B, "Mapped Track B", "Artist Two", "2024-01-03", 1, 200)
    register_observation(db, TRACK_UNMAPPED, "Unmapped Track", "Comma, Ampersand & Co", "2024-01-03", 3, 300)

    result = import_metadata_dataframe(
        db, metadata_frame(), "Authorized Metadata", "Client supplied; rights confirmed", "artists_albums.csv", MAPPING
    )
    assert result.imported_rows == 4
    assert result.rejected_rows == 0
    assert result.album_track_mappings == 3
    assert result.artist_track_mappings == 3

    albums = db.get_album_rankings(chart_type="daily", limit=50)
    assert [(row["album_id"], row["charting_track_streams"]) for row in albums] == [
        (ALBUM_ONE, 350),
        (ALBUM_EDITION, 150),
    ]
    album = db.get_album_detail(ALBUM_ONE, chart_type="daily")
    assert album is not None
    assert album["mapped_track_count"] == 2
    assert album["chart_appearances"] == 3
    assert [track["track_id"] for track in db.get_album_tracks(ALBUM_ONE, chart_type="daily")] == [TRACK_B, TRACK_A]

    artists = db.get_artist_summary(chart_type="daily", limit=50)
    by_key = {row["artist_key"]: row for row in artists}
    assert by_key[f"id:{ARTIST_ONE}"]["charting_song_streams"] == 150
    assert by_key[f"id:{ARTIST_TWO}"]["charting_song_streams"] == 350
    assert by_key["credit:Comma, Ampersand & Co"]["charting_song_streams"] == 300
    assert by_key["credit:Comma, Ampersand & Co"]["attribution"] == "Unresolved credited string; not split"

    filtered_album = db.get_album_detail(ALBUM_ONE, "2024-01-03", "2024-01-03", "daily")
    assert filtered_album is not None
    assert filtered_album["charting_track_streams"] == 250
    filtered_artist = db.get_artist_detail(f"id:{ARTIST_TWO}", "2024-01-03", "2024-01-03", "daily")
    assert filtered_artist is not None
    assert filtered_artist["charting_song_streams"] == 250

    repeated = import_metadata_dataframe(
        db, metadata_frame(), "Authorized Metadata", "Client supplied; rights confirmed", "artists_albums.csv", MAPPING
    )
    assert repeated.imported_rows == 4
    assert repeated.duplicates_skipped == 4
    assert repeated.album_track_mappings == 0
    assert repeated.artist_track_mappings == 0
    assert len(db.get_album_rankings(chart_type="daily", limit=50)) == 2


def test_metadata_import_rejects_bad_ids_and_conflicts_without_merging_editions(tmp_path: Path) -> None:
    db = DatabaseManager(tmp_path / "invalid_metadata.db")
    frame = metadata_frame().iloc[:1].copy()
    frame.loc[0, "Spotify Track ID"] = "similar-title-is-not-an-id"
    frame.loc[0, "Album Title"] = ""
    result = import_metadata_dataframe(
        db, frame, "Metadata", "Rights note", "bad.csv", MAPPING
    )
    assert result.rejected_rows == 1
    assert result.imported_rows == 0
    assert db.get_album_rankings() == []


def test_failed_metadata_transaction_rolls_back_provenance_and_mappings(tmp_path: Path) -> None:
    db = DatabaseManager(tmp_path / "rollback.db")
    db.connection.execute(
        """
        CREATE TRIGGER reject_test_album BEFORE INSERT ON albums
        BEGIN SELECT RAISE(ABORT, 'fixture failure'); END
        """
    )
    db.connection.commit()

    with pytest.raises(sqlite3.IntegrityError, match="fixture failure"):
        import_metadata_dataframe(
            db, metadata_frame().iloc[:1], "Metadata", "Rights note", "rollback.csv", MAPPING
        )

    assert db.connection.execute("SELECT COUNT(*) FROM metadata_import_batches").fetchone()[0] == 0
    assert db.connection.execute("SELECT COUNT(*) FROM track_albums").fetchone()[0] == 0
    assert db.connection.execute("SELECT COUNT(*) FROM sources WHERE name = 'Metadata'").fetchone()[0] == 0


def test_schema_upgrade_is_idempotent_and_preserves_existing_rows(tmp_path: Path) -> None:
    path = tmp_path / "migration.db"
    legacy = sqlite3.connect(path)
    legacy.executescript(
        """
        CREATE TABLE sources (id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, license TEXT, remarks TEXT, created_at TEXT);
        CREATE TABLE import_batches (batch_id TEXT PRIMARY KEY, source_name TEXT NOT NULL, source_license TEXT, chart_type TEXT NOT NULL, country TEXT NOT NULL, is_demo INTEGER NOT NULL DEFAULT 0, created_at TEXT);
        CREATE TABLE chart_records (
            id INTEGER PRIMARY KEY, batch_id TEXT NOT NULL, source TEXT NOT NULL,
            source_license TEXT, chart_type TEXT NOT NULL, country TEXT NOT NULL,
            chart_date TEXT NOT NULL, weekly_start TEXT, weekly_end TEXT,
            position INTEGER, track_id TEXT, track_name TEXT NOT NULL,
            artist_names TEXT NOT NULL, streams INTEGER NOT NULL, original_url TEXT,
            created_at TEXT,
            UNIQUE(source, chart_type, country, chart_date, position, track_name, artist_names, streams)
        );
        CREATE TABLE tracks (id INTEGER PRIMARY KEY, track_id TEXT NOT NULL UNIQUE, track_name TEXT, artist_names TEXT, source TEXT, created_at TEXT);
        CREATE TABLE artists (id INTEGER PRIMARY KEY, artist_id TEXT NOT NULL UNIQUE, artist_name TEXT, created_at TEXT);
        CREATE TABLE albums (id INTEGER PRIMARY KEY, album_id TEXT NOT NULL UNIQUE, album_name TEXT, created_at TEXT);
        CREATE TABLE track_artists (id INTEGER PRIMARY KEY, track_id TEXT NOT NULL, artist_id TEXT NOT NULL, attribution_rule TEXT DEFAULT 'primary-artist', is_primary INTEGER NOT NULL DEFAULT 1, UNIQUE(track_id, artist_id, attribution_rule));
        CREATE TABLE track_albums (id INTEGER PRIMARY KEY, track_id TEXT NOT NULL, album_id TEXT NOT NULL, mapping_confidence TEXT DEFAULT 'unknown', UNIQUE(track_id, album_id));
        INSERT INTO chart_records (batch_id, source, source_license, chart_type, country, chart_date, position, track_id, track_name, artist_names, streams)
        VALUES ('old-batch', 'Legacy user source', 'legacy license', 'daily', 'US', '2024-04-01', 1, 'old-track-id', 'Preserved', 'Artist', 900);
        INSERT INTO artists (artist_id, artist_name) VALUES ('legacy-artist-id', 'Legacy Artist');
        """
    )
    legacy.commit()
    legacy.close()

    upgraded = DatabaseManager(path)
    assert upgraded.connection.execute("PRAGMA user_version").fetchone()[0] == 1
    assert upgraded.connection.execute("SELECT streams FROM chart_records").fetchone()[0] == 900
    assert "metadata_batch_id" in {
        row["name"] for row in upgraded.connection.execute("PRAGMA table_info(track_albums)")
    }
    assert upgraded.connection.execute(
        "SELECT artist_name FROM artists WHERE artist_id = 'legacy-artist-id'"
    ).fetchone()[0] == "Legacy Artist"
    upgraded.close()

    reopened = DatabaseManager(path)
    assert reopened.connection.execute("SELECT COUNT(*) FROM chart_records").fetchone()[0] == 1
    reopened.close()


def test_artist_only_metadata_import_needs_no_album_identity(tmp_path: Path) -> None:
    db = DatabaseManager(tmp_path / "artist_only.db")
    frame = pd.DataFrame(
        [{"track_id": TRACK_A, "artist_id": ARTIST_ONE, "artist_name": "Artist One"}]
    )
    result = import_metadata_dataframe(
        db,
        frame,
        "Artist-only source",
        "Client supplied rights note",
        "artist_ids.csv",
        {"track_id": "track_id", "artist_id": "artist_id", "artist_name": "artist_name"},
    )
    assert result.imported_rows == 1
    assert result.artist_track_mappings == 1
    assert result.album_track_mappings == 0
