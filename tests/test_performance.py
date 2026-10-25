from __future__ import annotations

from datetime import date, timedelta
from time import perf_counter

from spotify_historical_analytics.db import DatabaseManager


def test_synthetic_chart_aggregation_benchmark(tmp_path) -> None:
    """Reproducible local benchmark; generated rows are test-only, not chart data."""
    db = DatabaseManager(tmp_path / "synthetic_benchmark.db")
    start = date(2017, 1, 1)
    rows = []
    for index in range(25_000):
        chart_day = start + timedelta(days=index % 100)
        track_number = index
        artist_number = track_number % 40
        rows.append(
            (
                "synthetic-benchmark",
                "SYNTHETIC BENCHMARK ONLY",
                "Generated test rows; not Spotify data",
                "daily",
                "US",
                chart_day.isoformat(),
                None,
                None,
                index % 250 + 1,
                f"synthetic-track-{track_number:04d}",
                f"Synthetic Track {track_number:04d}",
                f"Synthetic Artist {artist_number:02d}",
                1000 + index % 250,
                None,
            )
        )
    db.connection.executemany(
        """
        INSERT INTO chart_records (
            batch_id, source, source_license, chart_type, country, chart_date,
            weekly_start, weekly_end, position, track_id, track_name, artist_names,
            streams, original_url
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    db.connection.commit()

    started = perf_counter()
    summary = db.get_summary(chart_type="daily")
    summary_ms = (perf_counter() - started) * 1000
    started = perf_counter()
    songs = db.get_top_tracks(limit=200, chart_type="daily")
    songs_ms = (perf_counter() - started) * 1000
    started = perf_counter()
    artists = db.get_artist_summary(chart_type="daily", limit=200)
    artists_ms = (perf_counter() - started) * 1000
    print(
        f"synthetic_fixture_rows=25000 summary_ms={summary_ms:.2f} "
        f"songs_ms={songs_ms:.2f} artists_ms={artists_ms:.2f} "
        f"aggregate_queries_ms={summary_ms + songs_ms + artists_ms:.2f}"
    )

    assert summary["total_streams"] == sum(row[12] for row in rows)
    assert len(songs) == 200
    assert len(artists) == 40
