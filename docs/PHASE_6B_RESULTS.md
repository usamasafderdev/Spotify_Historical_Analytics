# Phase 6B Research Results

**Run date:** 2026-10-26  
**Scope:** Safe staging compaction, US chart quality checks, a space-guarded Kaggle latest-version preflight, and a research-only audit of Zenodo MGD+. No production data was modified or imported.

## Existing Dhruvil v85 chart audit

The source CSV is 3,483,476,388 bytes with SHA-256 `8238a106f723af9b1d3b857b78ec43f7147d82472b491c63853bcbcc3c23cb1b`. It contains 26,173,514 data rows.

| Classification | Rows | Treatment |
|---|---:|---|
| Accepted USA chart observations | 455,031 | Kept in separate research staging |
| Non-US or unknown region | 25,718,457 | Aggregated by reason and normalized source region; not staged as US |
| Out-of-range Viral 50 rank | 26 | Rejected and retained as bounded diagnostic samples |
| Total rejected | 25,718,483 | Count reconciles to source rows |

All 26 rank rejections were inspected. Each is `viral50` rank **51** (`position_out_of_range:50`), not a valid Top 200 observation. The compact report stores all 26 examples. Global rows were explicitly rejected; the aggregated rejection report counts 451,793 source rows with the source region value `Global`.

For daily Top 200, accepted records have actual stream values; no accepted Top 200 record had a NULL stream. Viral 50 observations have no stream values and must not be used in stream rankings. Counts and coverage remain source observations, not a claim that the publishing calendar is complete.

| Chart | Year | Rows | Dates with observations | Stream rows | Incomplete observed dates |
|---|---:|---:|---:|---:|---:|
| Top 200 | 2017 | 72,384 | 362 | 72,384 | 10 |
| Top 200 | 2018 | 73,000 | 365 | 73,000 | 0 |
| Top 200 | 2019 | 73,000 | 365 | 73,000 | 0 |
| Top 200 | 2020 | 73,200 | 366 | 73,200 | 0 |
| Top 200 | 2021 | 72,600 | 363 | 72,600 | 0 |
| Viral 50 | 2017 | 18,148 | 363 | 0 | 2 |
| Viral 50 | 2018 | 18,229 | 365 | 0 | 21 |
| Viral 50 | 2019 | 17,938 | 360 | 0 | 62 |
| Viral 50 | 2020 | 18,300 | 366 | 0 | 0 |
| Viral 50 | 2021 | 18,232 | 365 | 0 | 18 |

## Compact staging result

The new database is `D:\Study Material\University\Spotify-Dataset-Research\staging\research_staging_compact.sqlite`. The original `research_staging.sqlite` was read-only during the build and remains present.

- Source SHA-256 and source row counts were checked before and after processing.
- 26,173,514 rows reconciled to 455,031 accepted plus 25,718,483 rejected.
- Aggregated rejection counts sum to the rejected-row total.
- `PRAGMA integrity_check` returned `ok`.
- Compact database size: 325,226,496 bytes. Original database size: 13,912,154,112 bytes.
- The compact database contains canonical accepted observations, source provenance, aggregated rejection counts, and 46 bounded diagnostic samples. It is not a production data source.

The detailed storage design, space estimate, schema version, and safe handling notes are in [STAGING_STORAGE_AUDIT.md](./STAGING_STORAGE_AUDIT.md).

## Kaggle latest-version attempt

Public Kaggle listing metadata reported version 146 and 14,962,095,987 bytes for `gonzalopezgil/spotify-charts-daily-updated`. The exact-version cache paths were checked and no version 146 cache was found. At the preflight, 31,576,604,672 bytes were free. The conservative guard requires three times the listing size plus a 2 GiB reserve: 47,033,771,609 bytes.

The result is `SKIPPED_INSUFFICIENT_SPACE`. **The requested unversioned `dataset_download("gonzalopezgil/spotify-charts-daily-updated")` call was not made**, so this does not resolve the earlier pinned-version HTTP 404 and is not a failed latest-version response. No partial download was created. The machine-readable result is `reports\kaggle_latest_download_preflight.json` in the external research root.

## Zenodo MGD+ archive audit

The official Zenodo record 8086643 lists MGD+ under CC BY 4.0 and describes regional/global Top 200 charts from January 2017 through March 2022. This license statement applies to the record as published; it does not prove Spotify upstream, commercial analytics, or redistribution rights.

| Check | Measured result |
|---|---|
| Archive | `MGDplus.zip`, 364,603,433 bytes |
| Archive MD5 | `4e06a42f266f08d84e9cf6045c4ae3c3` (matches record metadata) |
| Archive SHA-256 | `93ad6b8dd7e8443fbfbece0d56bf74120073f69b1315706e305b995301e5392a` |
| CRC | Passed for all archive members |
| Members / uncompressed member sizes | 1,685 / 2,350,558,088 bytes |
| Unsafe member paths | 0 |
| Extraction / production import | Not performed |

The archive contains 68 regional market chart files plus a Global file, artist/song/network material, and 10 notebook-checkpoint CSVs. Its US chart member is a tab-delimited file with a `.csv` suffix. It contains only `Top 200`, not a Viral 50 chart file.

| US Top 200 measure | Result |
|---|---:|
| Rows | 378,800 |
| Market / chart labels | `us` / `Top 200` |
| Date span | 2017-01-01 to 2022-03-13 |
| Distinct observed dates | 1,893 |
| Distinct chart track IDs | 9,589 |
| Missing/invalid stream values, missing IDs, invalid ranks | 0 / 0 / 0 / 0 |
| Calendar-step gap candidates inside the observed span | 5 |
| Date with a non-200 row count | 2021-09-01: 400 rows |
| Duplicate identities on that date | 200; no duplicate stream-value conflicts detected |

The date gaps and the repeated date are data-quality observations, not a verified expected publication calendar. The duplicate identity check uses date, track ID, and rank; it does not prove every textual field is identical.

The US song metadata has `song_id`, `artist_id`, `release_date`, and a `total_streams` field; the chart records themselves have `ID`, credited artist text, rank, and per-chart `Streams`. Seven US artist metadata files include `artist_id`. No album-named fields were found in the inspected US song/artist metadata headers. Static song `total_streams` is not substituted for chart streams or interpreted as an official comprehensive album total.

### Cross-source key comparison

For the Dhruvil v85 date span, comparison identity is `(market, chart_type, chart_date, track_id)`; rank and streams are compared as observation fields. Duplicate rows are not summed and neither source is selected as authoritative.

| Year | Dhruvil unique Top 200 keys | MGD+ unique keys | Shared keys with same streams |
|---:|---:|---:|---:|
| 2017 | 72,384 | 72,200 | 72,185 |
| 2018 | 73,000 | 73,000 | 73,000 |
| 2019 | 73,000 | 72,800 | 72,800 |
| 2020 | 73,200 | 73,200 | 73,200 |
| 2021 | 72,600 | 73,000 | 72,600 |

Across 2017–2021, 363,785 identities were shared and all 363,785 had matching rank and stream values; 399 Dhruvildave identities and 415 MGD+ identities were unmatched within that period. The 2022 MGD+ rows are outside Dhruvildave v85's observed date span. Exact overlap supports technical consistency for matched rows only; the sources may not be independent and this does not establish correctness, completeness, or legal permission. The detailed refreshed results, including stable-artist-ID coverage and limitations, are in [MGDPLUS_VALIDATION_REPORT.md](./MGDPLUS_VALIDATION_REPORT.md) and [MGDPLUS_COMPARISON_REPORT.md](./MGDPLUS_COMPARISON_REPORT.md).

## Machine reports and remaining limitations

The reports are external to Git and the app database:

- `reports\phase6b_compact_audit\chart_quality_summary.json`
- `reports\phase6b_compact_audit\chart_quality_by_year.csv`
- `reports\phase6b_compact_audit\chart_quality_by_month.csv`
- `reports\phase6b_compact_audit\chart_quality_by_date.csv`
- `reports\phase6b_compact_audit\rejection_summary.csv`
- `reports\phase6b_compact_audit\invalid_rank_samples.csv`
- `reports\phase6b_zenodo_audited\zenodo_mgdplus_audit.json`
- `reports\phase6b_zenodo_audited\zenodo_mgdplus_archive_members.csv`
- `reports\phase6b_zenodo_audited\zenodo_mgdplus_us_chart_by_year.csv`
- `reports\phase6b_zenodo_audited\zenodo_mgdplus_us_chart_by_month.csv`
- `reports\phase6b_zenodo_audited\zenodo_mgdplus_us_chart_by_date.csv`

No source rights were approved, no source rows were imported into production, and no historical years are claimed complete. Remaining acquisition priorities are listed in [MISSING_YEARS_PLAN.md](./MISSING_YEARS_PLAN.md).
