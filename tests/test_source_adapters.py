from __future__ import annotations

import csv
import zipfile
from pathlib import Path

from spotify_historical_analytics.source_adapters import (
    DHRUVIL_COLUMNS,
    MGDPLUS_CHART_COLUMNS,
    iter_dhruvil_chart_batches,
    iter_mgdplus_artist_mappings,
    iter_mgdplus_us_chart_batches,
)


def _write_tsv(path: Path, columns: tuple[str, ...], rows: list[list[str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, delimiter="\t")
        writer.writerow(columns)
        writer.writerows(rows)


def test_mgdplus_adapter_streams_us_rows_and_retains_invalid_provenance(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "mgdplus-fixture.zip"
    member = "charts/regional/spotify_charts_regional_us.csv"
    chart = (
        "track-1\tSynthetic song\tSynthetic artist\t1\t1,234\tup\t2022-01-02\tTop 200\tUS\n"
        "track-2\tOther song\tOther artist\t2\tbad\tflat\t2022-01-02\tTop 200\tUS\n"
        "track-3\tCanada song\tOther artist\t3\t500\tdown\t2022-01-02\tTop 200\tCA\n"
    )
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(member, "\t".join(MGDPLUS_CHART_COLUMNS) + "\n" + chart)

    batches = list(iter_mgdplus_us_chart_batches(archive_path, chunk_size=2))

    assert [len(batch) for batch in batches] == [2, 1]
    valid, invalid_stream, non_us = [row for batch in batches for row in batch]
    assert valid.valid
    assert valid.market == "US"
    assert valid.chart_name == "Top 200"
    assert valid.cadence == "daily"
    assert valid.chart_date == "2022-01-02"
    assert valid.track_id == "track-1"
    assert valid.streams == 1234
    assert valid.source_file == f"{archive_path.name}:{member}"
    assert len(valid.source_sha256) == 64
    assert invalid_stream.error == "invalid_stream_count"
    assert non_us.error == "non_us_market"


def test_mgdplus_artist_adapter_preserves_multiple_exact_credits(
    tmp_path: Path,
) -> None:
    archive_path = tmp_path / "metadata-fixture.zip"
    metadata_member = "songs/regional/us/synthetic.tsv"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(
            metadata_member,
            "song_id\tartist_id\ntrack-1\t['artist-a', 'artist-b']\ntrack-2\tartist-c\n",
        )

    batches = list(
        iter_mgdplus_artist_mappings(
            archive_path, (metadata_member,), chunk_size=1
        )
    )

    assert batches == [
        [("track-1", ("artist-a", "artist-b"))],
        [("track-2", ("artist-c",))],
    ]


def test_dhruvil_adapter_keeps_viral_rows_streamless_and_ids_url_verified(
    tmp_path: Path,
) -> None:
    path = tmp_path / "dhruvil-fixture.csv"
    valid_id = "0123456789ABCDEFGHIJKL"
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(DHRUVIL_COLUMNS)
        writer.writerow(
            [
                "Song",
                "1",
                "2019-03-04",
                "Artist",
                f"https://open.spotify.com/track/{valid_id}",
                "United States",
                "top200",
                "up",
                "12345",
            ]
        )
        writer.writerow(
            [
                "Viral song",
                "2",
                "2019-03-04",
                "Artist",
                f"https://open.spotify.com/track/{valid_id}",
                "US",
                "viral50",
                "flat",
                "",
            ]
        )
        writer.writerow(
            [
                "Untrusted URL",
                "3",
                "2019-03-04",
                "Artist",
                f"https://example.com/track/{valid_id}",
                "US",
                "top200",
                "flat",
                "100",
            ]
        )

    rows = [
        row
        for batch in iter_dhruvil_chart_batches(path, chunk_size=2)
        for row in batch
    ]

    top200, viral50, untrusted_url = rows
    assert top200.valid and top200.track_id == valid_id
    assert top200.streams == 12345
    assert top200.cadence == "daily"
    assert viral50.valid and viral50.chart_name == "viral50"
    assert viral50.streams is None
    assert not untrusted_url.valid
    assert untrusted_url.track_id is None
    assert untrusted_url.error == "missing_verified_spotify_track_id"


def test_adapters_reject_wrong_schema_and_invalid_chunk_sizes(tmp_path: Path) -> None:
    path = tmp_path / "wrong-schema.csv"
    path.write_text("title,rank\n", encoding="utf-8")

    try:
        list(iter_dhruvil_chart_batches(path))
    except ValueError as error:
        assert "missing columns" in str(error)
    else:
        raise AssertionError("wrong Dhruvil schema must be rejected")

    with zipfile.ZipFile(tmp_path / "empty.zip", "w"):
        pass
    try:
        list(iter_mgdplus_us_chart_batches(tmp_path / "empty.zip", chunk_size=0))
    except ValueError as error:
        assert "chunk_size" in str(error)
    else:
        raise AssertionError("non-positive chunk size must be rejected")
