# Supported historical data schema

US Music Charts Analytics 0.1.0. Data import runs inside the Windows application; Python and VS Code are not required. This document describes the local-file importer, not the separate research pipeline.

## Files and required columns

Use UTF-8 CSV (optionally with a byte-order mark), CSV.GZ, or XLSX. CSV detection supports comma, tab, or semicolon delimiters. XLSX reads the active worksheet with the first row as headers; formulas are not calculated. Export calculated values before importing. Compressed CSV is streamed; ZIP archives, Parquet, JSON, and XLSM are not supported client import formats.

Known compatible/MGD+/Dhruvil schemas are recognized automatically. Other names can be mapped in the same dialog. Each required field must map to a distinct source column. Header aliases ignore case and punctuation; the following preferred headers avoid ambiguity.

| Preferred header | Required | Meaning |
|---|---|---|
| `date` | Yes | Chart observation date; use ISO `YYYY-MM-DD`. |
| `track_name` | Yes | Nonempty song title. |
| `artist_names` | Yes | Nonempty whole credited-artist string. This is not split into people. |
| `streams` | Yes | Whole nonnegative stream count from the chart observation. Zero is valid; missing/negative/nonfinite/fractional values reject. Individual values must fit signed 64-bit SQLite integers. |
| `country` | Yes | USA market. Prefer `US`; supported USA aliases normalize to US. Other countries reject. |

Dates also recognize `YYYY/MM/DD`, `MM/DD/YYYY`, and `DD/MM/YYYY`, but ambiguous slash dates are interpreted month-first. Use ISO dates for reliable exchange. XLSX date cells are accepted. Files need a header row; duplicate headers reject.

## Optional identity and chart columns

| Header | Meaning / requirement |
|---|---|
| `track_id` | Stable track identifier; strongly recommended. Without it, compatible tables use exact title plus whole credited string as a conservative identity. |
| `url` | Optional supported track URL/URI from which a stable ID can be extracted. Stored as text; no track is fetched. |
| `position` | Positive integer chart rank when supplied. Recognized source adapters require it. |
| `chart_type` | `daily` or `weekly`; otherwise choose the cadence in the dialog. A mixed file imports only the selected cadence. |
| `weekly_start`, `weekly_end` | Both required for weekly imports, with start on or before end. Supply the actual source reporting interval; the app does not reconstruct daily counts. |

Daily and weekly totals are separate. The app sums the imported chart count as supplied; it does not divide weekly totals into days, manufacture absent observations, or treat sampled weekly dates as complete daily history. Source-specific recognized adapters impose additional category/ID checks and reject streamless Viral rows.

## Artist and album relationships

For stable artist attribution supply `track_id`, `artist_id`, and `mapped_artist_name`. The last column maps to the resolved artist name, independently of `artist_names`. An ID without a resolved name is not used for artist attribution. Without supplied associations the app retains the whole credited string as an unresolved group. It does not infer IDs from names.

For collaborations, repeat an otherwise identical chart observation with a different supplied artist ID/resolved name per collaborator. Keep its title, whole credit string, date, position, and streams identical. The observation is imported once while distinct supplied relationships are retained. Each mapped artist receives full credit; artist totals can overlap.

For albums supply `track_id`, `album_id`, and `album_name`. Optional `album_artist`, `release_date`, and `source_reference` improve labels/provenance. An album ID without its name rejects the row. Distinct album IDs remain separate editions, even when their names match. Association-only files are not a separate client import flow; provide associations alongside chart observations. Avoid title-only fallback identities for accurate cross-source album work.

These are user-supplied exact associations, not independently authenticated platform metadata. Conflicting names or album metadata for an existing ID can block the transaction. Without stable mappings, album rankings stay empty.

## Validation and coverage

Review source name, detected cadence, date range, valid USA counts, rejections, duplicate counts, and warnings before importing. The dialog shows actual observed coverage, not a completeness certification. Existing source/track/date identities with conflicting values block import. Duplicates are prevented within the source context; different overlapping sources are not automatically reconciled into a canonical history. Use a consistent source name on repeat imports.

Validation stages rows in chunks of 2,000; final production changes are transactional. File hashes detect changes between validation and import. Cancellation rolls back a production transaction. A pre-import backup is created, so allow additional disk space for the input, staging database, production growth, and backups. Very large imports can take minutes. No fixed maximum row count or silently truncated preview is an import limit. Very large aggregate totals remain subject to SQLite numeric limits and spreadsheet numeric precision.

## Synthetic example only

The following values and identifiers are invented for testing and are not historical Spotify observations. Use a source name such as `SYNTHETIC TRAINING ONLY` in an isolated test directory; do not add training fixtures to a live client database.

```csv
date,track_name,artist_names,streams,country,track_id,position,chart_type,artist_id,mapped_artist_name,album_id,album_name
2024-01-01,Synthetic Song A,Synthetic Artist A,100,US,synthetic-track-a,1,daily,synthetic-artist-a,Synthetic Artist A,synthetic-album-a,Synthetic Album A
2024-01-02,Synthetic Song A,Synthetic Artist A,120,US,synthetic-track-a,2,daily,synthetic-artist-a,Synthetic Artist A,synthetic-album-a,Synthetic Album A
```

Expected chart-stream sum: **220**. Importing the unchanged file again under the same source must add zero observations. The same chart observations map to one artist and one album, each with charting-track/song streams of 220.

No historical dataset is bundled. Importing a file does not grant acquisition, commercial-use, analysis, export, or redistribution rights. The client must resolve source scope and permissions separately.
