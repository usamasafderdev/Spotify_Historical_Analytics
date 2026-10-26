from __future__ import annotations

from datetime import date, timedelta
import threading
from time import perf_counter
import tracemalloc

import pytest

from spotify_historical_analytics.db import DatabaseManager


@pytest.mark.parametrize("row_count", [25_000, 100_000, 500_000])
def test_synthetic_chart_import_and_query_benchmark(tmp_path, row_count: int) -> None:
    """Measure bounded synthetic loads; generated rows are not chart data."""
    db_path = tmp_path / f"synthetic_benchmark_{row_count}.db"
    db = DatabaseManager(db_path)
    start = date(2017, 1, 1)
    batch_size = 5_000
    inserted = 0
    try:
        import psutil
    except ImportError:
        process = None
    else:
        process = psutil.Process()
    rss_samples: list[int] = []
    stop_sampling = threading.Event()
    sampler = None
    if process is not None:
        def sample_rss() -> None:
            while not stop_sampling.is_set():
                rss_samples.append(process.memory_info().rss)
                stop_sampling.wait(0.01)

        sampler = threading.Thread(target=sample_rss, daemon=True)
        sampler.start()
    tracemalloc.start()
    import_started = perf_counter()
    while inserted < row_count:
        end = min(inserted + batch_size, row_count)
        rows = [
            (
                f"synthetic-batch-{row_index // batch_size:03d}",
                "SYNTHETIC BENCHMARK ONLY",
                "Generated test rows; not Spotify data",
                "daily",
                "US",
                (start + timedelta(days=row_index % 100)).isoformat(),
                None,
                None,
                row_index % 250 + 1,
                f"synthetic-track-{row_index:06d}",
                f"Synthetic Track {row_index:06d}",
                f"Synthetic Artist {row_index % 250:03d}",
                1000 + row_index % 250,
                None,
            )
            for row_index in range(inserted, end)
        ]
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
        inserted = end
    db.connection.commit()
    import_seconds = perf_counter() - import_started
    _, peak_python_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    query_times: dict[str, float] = {}
    for label, query in (
        ("summary", lambda: db.get_summary(chart_type="daily")),
        ("songs", lambda: db.get_top_tracks(limit=200, chart_type="daily")),
        ("artists", lambda: db.get_artist_summary(chart_type="daily", limit=200)),
    ):
        started = perf_counter()
        result = query()
        query_times[label] = (perf_counter() - started) * 1000
        if label == "summary":
            assert result["total_streams"] == sum(
                1000 + row_index % 250 for row_index in range(row_count)
            )
        elif label == "songs":
            assert len(result) == 200
        else:
            assert len(result) == 200

    query_plan = db.connection.execute(
        """
        EXPLAIN QUERY PLAN
        SELECT COUNT(*) FROM chart_records
        WHERE country='US' AND chart_type='daily' AND chart_date >= ?
        """,
        ("2017-01-01",),
    ).fetchall()
    plan_text = " ".join(str(row["detail"]) for row in query_plan)
    assert "idx_chart_records_market_type_date" in plan_text
    if sampler is not None:
        stop_sampling.set()
        sampler.join()
    peak_rss_mib = (
        max(rss_samples) / 1024 / 1024 if rss_samples else None
    )
    db.close()
    database_bytes = db_path.stat().st_size

    print(
        f"synthetic_rows={row_count} import_seconds={import_seconds:.3f} "
        f"peak_python_mib={peak_python_bytes / 1024 / 1024:.2f} "
        f"peak_process_rss_mib={peak_rss_mib if peak_rss_mib is not None else 'unavailable'} "
        f"query_ms={query_times} database_mib={database_bytes / 1024 / 1024:.2f} "
        f"index_plan={plan_text}"
    )
