# Supported historical data schema

US Music Charts Analytics 0.1.8 development source. Historical dataset integration and packaged verification are pending. This document describes the local-file importer, not the separate research pipeline.

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
| `weekly_start`, `weekly_end` | Required for custom weekly tables unless an original Spotify weekly filename supplies an unambiguous period (below). Seven inclusive calendar days, with the observation date inside that interval. The app does not reconstruct daily counts. |

Daily and weekly totals are separate. The app sums the imported chart count as supplied; it does not divide weekly totals into days, manufacture absent observations, or treat sampled weekly dates as complete daily history. Source-specific recognized adapters impose additional category/ID checks and reject streamless Viral rows.

The **Weekly (from daily)** view computes Monday-Sunday periods from existing daily observations, reports each on Sunday, and filters by that reporting date. Partial weeks remain partial: missing observations are never filled. This view does not write derived rows into SQLite or combine them with source weekly observations. Song tooltips include the number of observed days.

**Import Weekly CSV** accepts one or multiple CSV, CSV.GZ, or XLSX files. Custom tables need the required fields above and explicit week boundaries. Original Spotify exports are recognized by their legacy `Position,Track Name,Artist,Streams,URL` or current `rank,uri,artist_names,track_name,streams` headers and an intact `regional-us-weekly-...` filename. These files can omit custom date/country/week columns: the importer reads the market and period from the recognized filename. A legacy introductory Spotify note is supported.

Recognized filenames identify a Thursday week end (`regional-us-weekly-2024-02-08.csv`) or an explicit Friday-to-Friday/Thursday range (`regional-us-weekly-2024-02-02--2024-02-09.csv` or `...--2024-02-08.csv`). Friday end boundaries are exclusive and normalized to the preceding Thursday. Legacy Thursday-to-Thursday names (`...-2024-02-01--2024-02-08.csv`) use the preceding Thursday as an exclusive start boundary. All these recognized forms normalize to February 2-8, reported on Thursday, corresponding to Spotify's published [Friday-through-Thursday charting week](https://support.spotify.com/us/artists/article/understanding-spotify-charts/). The same names work for CSV.GZ and XLSX conversions. Conflicting explicit fields, non-US markets, invalid ranges, and ambiguous filenames reject; renamed/custom tables must provide their own date, country, and week boundaries. MGD+/Dhruvil daily chart category labels alone do not establish a weekly period.

The dedicated weekly workflow requires a valid **22-character alphanumeric Spotify track ID**, a supported Spotify track URL, or a `spotify:track:ID` URI. This is stricter than the general compatible-table importer, which permits exact title/credit fallback and legacy synthetic identifiers. Artist and album metadata must still provide their own exact IDs and names; track IDs are never used to invent those associations. Chart position is a positive integer when supplied. Files are validated in full; any invalid row or conflicting observation blocks that file. Each file commits transactionally; other selected files can succeed, and the result summary reports each outcome. No automatic full-database copies are made by this weekly workflow.

## Artist and album relationships

For stable artist attribution supply `track_id`, `artist_id`, and `mapped_artist_name`. The last column maps to the resolved artist name, independently of `artist_names`. An ID without a resolved name is not used for artist attribution. Without supplied associations the app retains the whole credited string as an unresolved group. It does not infer IDs from names.

For collaborations, repeat an otherwise identical chart observation with a different supplied artist ID/resolved name per collaborator. Keep its title, whole credit string, date, position, and streams identical. The observation is imported once while distinct supplied relationships are retained. Each mapped artist receives full credit; artist totals can overlap.

For albums supply `track_id`, `album_id`, and `album_name`. Optional `album_artist`, `release_date`, and `source_reference` improve labels/provenance. An album ID without its name rejects the row. Distinct album IDs remain separate editions, even when their names match. Associations may accompany observations or be imported separately with **Settings > Import artist / album metadata**. Avoid title-only fallback identities for accurate cross-source album work.

These are user-supplied exact associations, not independently authenticated platform metadata. Conflicting names or album metadata for an existing ID can block the transaction. Without stable mappings, album rankings stay empty.

## Validation and coverage

Review source name, detected cadence, date range, valid USA counts, rejections, duplicate counts, and warnings before importing. The dialog shows actual observed coverage, not a completeness certification. Existing track/date/chart-type identities with conflicting values block import across production sources. Exact overlapping observations are skipped. Analytics count each identity once even if duplicate records already exist, using the earliest stored record; legacy conflicts must be reviewed before genuine dataset integration. Demo observations remain separate.

Repeat indicators count distinct reporting dates per stable song/artist/album identity across the full selected range and chart type, before Top N. Multiple charting tracks on the same date count as one artist/album appearance. Unresolved credit strings are labeled without asserting repeat artist identity. Aggregated rankings retain one row per entity and unchanged totals.

Open **Chart showings** from Songs, Artists, or Albums to see individual reporting-date appearances using the page's current date range, chart source, search, and Top N limit. Only entities with known stable IDs appear here; unresolved groups remain available in the aggregated rankings. **Hide Repeats** visibly removes additional showings and retains one representative per entity according to the dialog's selected sort: highest streams, best position, newest date, or oldest date. Sorting and repeat filtering run over the complete eligible history; the list limit is applied last. Appearance counts also use that complete history, so an entity with 60 appearances still shows `Repeat (60)` when the visible limit is 50. Turning the option off shows all eligible appearances up to the limit. No records are deleted or stream totals changed. The page checkbox supplies the initial dialog setting and reflects its final state; it does not change aggregated rankings.

SQLite schema version 2 remains compatible: observations live in `chart_records`; stable entities and exact mappings use `tracks`, `artists`, `albums`, `track_artists`, and `track_albums`. Later seed integration must merge through validated imports into the user database, never replace it. **Settings** provides user-requested backups and restore; restore checks integrity/schema and saves the previous database first.

Validation stages rows in chunks of 2,000; final production changes are transactional. File hashes detect changes between validation and import. Cancellation rolls back a production transaction. The general **Import Dataset** dialog creates a pre-import backup; the dedicated weekly workflow uses transactional writes without automatically copying the database. Allow space for input, staging, production growth, and any backups you create. Very large imports can take minutes. No fixed maximum row count or silently truncated preview is an import limit. Very large aggregate totals remain subject to SQLite numeric limits and spreadsheet numeric precision.

## Synthetic example only

The following values and identifiers are invented for testing and are not historical Spotify observations. Use a source name such as `SYNTHETIC TRAINING ONLY` in an isolated test directory; do not add training fixtures to a live client database.

```csv
date,track_name,artist_names,streams,country,track_id,position,chart_type,artist_id,mapped_artist_name,album_id,album_name
2024-01-01,TEST DATA Song A,TEST DATA Artist A,100,US,AAAAAAAAAAAAAAAAAAAAAA,1,daily,BBBBBBBBBBBBBBBBBBBBBB,TEST DATA Artist A,CCCCCCCCCCCCCCCCCCCCCC,TEST DATA Album A
2024-01-02,TEST DATA Song A,TEST DATA Artist A,120,US,AAAAAAAAAAAAAAAAAAAAAA,2,daily,BBBBBBBBBBBBBBBBBBBBBB,TEST DATA Artist A,CCCCCCCCCCCCCCCCCCCCCC,TEST DATA Album A
```

Expected chart-stream sum: **220**. Importing the unchanged file again under the same source must add zero observations. The same chart observations map to one artist and one album, each with charting-track/song streams of 220.

These 22-character identifiers are invented TEST DATA, not verified Spotify entities. This example is **daily** and belongs in the general importer. To test the dedicated weekly importer, supply `chart_type=weekly` and explicit `weekly_start`/`weekly_end` (for example, `2024-02-02`/`2024-02-08`) with one observation dated inside that week; do not relabel daily observations as genuine weekly history.

No historical dataset is bundled. Importing a file does not grant acquisition, commercial-use, analysis, export, or redistribution rights. The client must resolve source scope and permissions separately.
