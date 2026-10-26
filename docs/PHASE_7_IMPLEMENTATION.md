# Phase 7 Implementation

## Scope delivered

- Added bounded, read-only adapters for the verified MGD+ US regional TSV schema and Dhruvil CSV schema. Both report source file, SHA-256, and source row number for every adapted row; schema mismatches fail explicitly.
- MGD+ rows retain exact track IDs, chart labels, rank, date, trend, streams, and market. No weekly dates or album mappings are inferred.
- MGD+ song metadata can be streamed as exact `song_id` to multiple `artist_id` mappings. IDs are not guessed by splitting credited display names.
- Dhruvil track IDs are accepted only from a Spotify `open.spotify.com/track/<22-character-id>` URL. `viral50` records keep their original chart label and are always streamless in the canonical adapter. Cadence is daily because the verified source file schema contains no weekly-period fields; the adapter does not invent weekly records.
- Rights approval now requires written evidence plus explicit acquisition, derived-analytics, commercial-use, and redistribution scopes. The evidence SHA-256 and scope record are retained. `APPROVED` means that evidence was recorded after human review; the program does not independently establish that a contract is valid or that the reviewer has authority.
- Coverage inventory now reports valid stream rows, unique stable track IDs, artist/album mapping counts, observed date range, rights status, and import status. The page displays 2017–2026 and states that research staging is isolated and not loaded into the application.
- Added repeatable 25k, 100k, and 500k synthetic SQLite batch-insert benchmarks. Measurements below were produced by `python -m pytest -q -s tests/test_performance.py`; no research or production data is used. Peak memory is Python `tracemalloc` allocation, not total process RSS.

## Deliberate safety boundaries

- Adapters are not invoked by application startup and do not write to the production database.
- Dhruvil and MGD+ research files and staging databases remain external to the application and Windows package.
- No source is approved by this change. MGD+ and Dhruvil remain `UNVERIFIED`.
- No migration or copy from research staging to production was performed.
- Existing user-file imports remain available and record a rights warning in source provenance. A license note entered by a user is not independent proof of permission.
- Observed date counts and missing-date candidates are not assertions of completeness or zero activity.

## Verification status

The complete suite passed: **91 tests**. `python -m compileall -q src scripts tests` and `git diff --check` passed. The Windows EXE was rebuilt and its empty-database launch, CSV/XLSX export, and isolated `--demo-smoke-test` all exited successfully. Build output is `dist/USMusicChartsAnalytics/USMusicChartsAnalytics.exe` with SHA-256 `C7E34857F7DAB3B80E8DC5291A15C1D83CC8A1AC5D607CF82CC4E92CFD74EF79`. PyInstaller emitted a non-fatal warning for optional `pyqtgraph.opengl` because `OpenGL` is not installed; the application does not use that optional module.

The per-user production database was queried read-only at `%LOCALAPPDATA%\USMusicChartsAnalytics\database\analytics.db`: **0 chart rows** (0 synthetic rows). The external research staging database at `D:\Study Material\University\Spotify-Dataset-Research\staging\research_staging_compact.sqlite` was also queried read-only: **455,031 observations**, comprising 364,184 US daily Top 200 rows with streams and 90,847 US daily Viral 50 rows without streams, all dated 2017-01-01 through 2021-12-31. It records zero approved sources and remains outside the application. No production/import writes were performed.

Inno Setup 6 (`ISCC.exe`) is not installed, so the installer was not built. Native desktop visual checks at 1366x768, 1600x900, 1920x1080 and 100%, 125%, 150% DPI were not performed; offscreen widget checks are not a substitute. No signed release is claimed.

### Measured synthetic benchmark

| Rows | Batched insert (s) | Peak Python allocations (MiB) | Summary query (ms) | Top songs (ms) | Top artists (ms) | SQLite file (MiB) |
|---:|---:|---:|---:|---:|---:|---:|
| 25,000 | 2.148 | 4.75 | 47.68 | 77.59 | 53.70 | 15.16 |
| 100,000 | 23.643 | 4.76 | 414.13 | 708.07 | 484.22 | 61.20 |
| 500,000 | 148.383 | 4.76 | 12,105.39 | 8,614.07 | 11,273.50 | 302.04 |

The date/market/chart query used `idx_chart_records_market_type_date` as a covering index at every size. The 500k-row analytics latency is material despite the index and the UI's background-worker pattern; these synthetic results are not a release performance guarantee. Query-plan and aggregation optimization on representative authorized records should be completed before client-scale delivery.

## Known gaps before client delivery

- The GUI import experience is not yet a complete 13-stage, persisted approval workflow; the command-level rights gate applies to research-staging production imports, while manual user-file imports retain their explicit user-supplied provenance warning.
- The canonical source adapters are not an automatic route into production; an authorized source/version must be separately staged, reviewed, and imported using the gated pipeline.
- Legal permission and upstream data rights remain unverified.
- Production historical coverage, 2022–2026 coverage, and source completeness remain unverified.
- The application cannot infer album editions from either research source; exact album metadata remains a separate authorized import.
