# MGD+ Dataset Validation Report

**Review date:** 2026-10-26  
**Purpose:** Research-only validation of the supplied MGD+ archive against the US chart schema. No production import, app database write, archive extraction, or EXE bundling was performed.

## Files and integrity

The supplied file is `D:\Downloads\MGDplus.zip`. An existing research copy was also present at `D:\Study Material\University\Spotify-Dataset-Research\03_Zenodo_MGDplus\MGDplus.zip`; no duplicate was downloaded. Both files are 364,603,433 bytes and have SHA-256 `93ad6b8dd7e8443fbfbece0d56bf74120073f69b1315706e305b995301e5392a`.

The ZIP CRC test passed for all 1,685 members. The archive contains 2,350,558,088 uncompressed member bytes and no unsafe member paths. It was read directly using ZIP streaming; it was not extracted.

The actual US chart member is `charts/regional/spotify_charts_regional_us.csv`. Despite the suffix, it is tab-delimited. Its columns are:

`ID`, `Track`, `Artist`, `Position`, `Streams`, `Trend`, `Date`, `Chart`, `market`

The six US song-metadata files are:

- `songs/regional/us/us-hit_songs-2017.csv`
- `songs/regional/us/us-hit_songs-2018.csv`
- `songs/regional/us/us-hit_songs-2019.csv`
- `songs/regional/us/us-hit_songs-2020.csv`
- `songs/regional/us/us-hit_songs-2021.csv`
- `songs/regional/us/us-hit_songs-2022.csv`

The seven artist files are:

- `artists/us/us-artists-2017.csv`
- `artists/us/us-artists-2018.csv`
- `artists/us/us-artists-2019.csv`
- `artists/us/us-artists-2020.csv`
- `artists/us/us-artists-2021.csv`
- `artists/us/us-artists-2022.csv`
- `artists/us/us-artists-all_time.csv`

Their exact headers and data-row counts are in the machine audit report.

## USA observations and time coverage

All 378,800 rows in the US chart member identify market `us` and chart `Top 200`; all pass the observed date, rank, and stream parsing checks.

| Year | Chart rows with streams | Notes |
|---:|---:|---|
| 2017 | 72,200 | 362 dates observed |
| 2018 | 73,000 | 365 dates observed |
| 2019 | 72,800 | 365 dates observed |
| 2020 | 73,200 | 366 dates observed |
| 2021 | 73,200 | 365 dates observed, including repeated identities |
| 2022 | 14,400 | Observed through March 13 only |
| 2023–2026 | 0 | No chart rows in this archive |

Observed dates span **2017-01-01 through 2022-03-13**, with 1,893 distinct dates. Five calendar dates inside that span have no rows. These are calendar-step gap candidates, not proof of missing publication records; the source's expected publishing schedule is not verified. One date has 400 rows instead of 200, forming 200 duplicated date/track/rank identities. No duplicated identity has conflicting stream values.

The chart has actual per-observation `Streams` values: 0 missing, 0 invalid, and ranks 1–200. It has 9,589 distinct 22-character track IDs. There is no Viral chart member. No weekly chart series was identified in the US chart file; the observed chart is daily Top 200.

`Trend` is a separate field and was not interpreted as streams. The song metadata includes `popularity` and `total_streams`; neither was substituted for a dated chart observation. Metadata `total_streams` is not used in chart totals.

## Track and artist metadata

The US song metadata provides stable `song_id` values for all **9,589** distinct chart track IDs. Every chart track ID matches a song metadata ID. The metadata's `artist_id` field contains either one ID or a serialized list of IDs; list parsing uses a literal parser and does not execute input. All chart track IDs have an artist-ID mapping; 3,690 have multiple artist IDs, which represent multiple credits and must not be split or attributed heuristically.

The seven artist metadata files contain 2,061 distinct artist IDs, and all 2,061 artist IDs found through the chart-track mappings match an artist metadata ID.

The inspected US song and artist metadata headers contain no album-related fields. MGD+ therefore does not provide the stable track-to-album mapping needed for album analytics.

## Dataset rights and isolation

The Zenodo record states CC BY 4.0 for its published record. That statement does not resolve upstream Spotify content rights, commercial derived-analytics permission, or redistribution. The dataset permission state remains **UNVERIFIED**.

No MGD+ records were copied into the client production database or an application validation database. Because rights remain unverified, adapter and comparison behavior is covered using small synthetic, schema-compatible test archives. The source archive is not bundled in the application or Windows executable.

## Reproduction

From the repository root:

```powershell
python scripts\audit_mgdplus_archive.py `
  --archive "D:\Downloads\MGDplus.zip" `
  --report-dir "D:\Study Material\University\Spotify-Dataset-Research\reports\phase6c_mgdplus_final" `
  --compact-db "D:\Study Material\University\Spotify-Dataset-Research\staging\research_staging_compact.sqlite" `
  --start-year 2017 --end-year 2026
```

The command refuses to overwrite an existing report directory. It reads the ZIP and compact research database without importing rows into production.

## Verification and changed files

- `python -m pytest -q` — **84 passed**.
- `python -m pytest -q tests/test_phase6_research_pipeline.py -k mgdplus` — **3 passed**.
- `python -m compileall -q scripts tests src` with a temporary bytecode cache — passed.
- `git diff --check` — passed.

Repository files changed for this validation: `scripts/audit_mgdplus_archive.py`, `tests/test_phase6_research_pipeline.py`, `README.md`, `docs/PHASE_6B_RESULTS.md`, `docs/MGDPLUS_VALIDATION_REPORT.md`, and `docs/MGDPLUS_COMPARISON_REPORT.md`. The ZIP and machine reports remain outside the repository and the application database.

## Limitations and next steps

This audit establishes file structure and observed rows only. It does not authenticate the publisher's upstream rights, prove completeness, establish publication cadence, or approve commercial use. The archive supplies no 2022-after-March or 2023–2026 chart rows, no Viral chart series, and no album mappings. Obtain written rights approval and independent source provenance review before considering any commercial processing or import.
