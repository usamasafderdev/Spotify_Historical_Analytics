# Phase 3: Artist, Album, and Background Analytics

## Implemented

- Artist rankings use supplied stable artist IDs where exact track-to-artist mappings exist. Each supplied ID receives full credit for the mapped chart row. Multiple artist IDs therefore overlap by design.
- Without a stable artist ID mapping, credited artist text remains a single unresolved identity. Artist names are not split on commas, ampersands, or other punctuation.
- Top Artists supports search, top 50/100/200, sortable ranking, track and observation counts, best position, first/latest dates, and an artist detail trend.
- Metadata import supports CSV/XLSX preview, user-selectable columns, source/license attribution, row validation, duplicate reporting, and per-row rejection details.
- Top Albums uses only exact user-supplied track-ID / album-ID mappings. Rankings show **Album charting-track streams**, mapped track count, chart observations, and best position. Album details include the mapped track list and trend.
- Multiple album IDs are preserved as separate editions. A charting track can contribute to more than one edition; album totals across editions can overlap.
- Existing chart observations without album mappings are omitted from album rankings. Unknown album data is not guessed.
- Dashboard aggregation loads through a query worker. Chart and metadata imports use worker-owned SQLite connections and atomic transactions. Imports are not cancelable once the transaction starts.
- SQLite schema upgrades are additive and idempotent; `PRAGMA user_version` is now 1. Existing user records are retained.
- Search, sort, details, date and chart filters use parameterized SQLite queries. Ranking tables are capped at 200 rows per selected view.

## Schema changes

Existing `artists`, `albums`, `track_artists`, and `track_albums` tables are preserved. Additive columns record metadata source, license note, import batch, release date, mapping status, and confidence. A `metadata_import_batches` table records file/source provenance and accepted/rejected/duplicate counts. New indexes support chart filters and relationship joins.

## Metrics and limitations

- Artist aggregates are full-credit per mapped artist ID; their sum is not a unique chart-stream total. Unresolved credited strings are displayed without parsing.
- Album totals sum imported chart observations for mapped tracks only. They do not represent Spotify's comprehensive album totals and may overlap across editions.
- User-supplied stable IDs are exact mapping keys, not independent proof of identity or license rights. No platform metadata is fetched.
- Artist/album search refresh and detail queries execute directly for a bounded page; dashboard-wide aggregate refresh runs asynchronously. Very large searches may still take noticeable time.
- Background work shows an indeterminate progress dialog but does not support cancellation. Closing the application waits for active background tasks.
- Album exports are not implemented; the existing project had no export infrastructure.
- The application and charts still require manual visual review on a Windows desktop.

## Verification

`python -m pytest -q` covers legacy foundation behavior, artist attribution, artist-only metadata, album mapping and editions, date filters, metadata re-import idempotence, CSV/XLSX preview and import, rollback, additive migration, Qt navigation/filter smoke tests, and a background import worker. Latest full run: **19 passed**.

Run the synthetic local query benchmark with:

```powershell
python -m pytest -q -s tests/test_performance.py
```

That test creates only clearly labeled test rows in a temporary SQLite database and prints measured aggregate query timings. It is not Spotify data and does not establish production-scale performance.

Latest local measurement from `python -m pytest -q -s` on a 25,000-row synthetic fixture: summary **281.30 ms**, songs **385.34 ms**, artists **455.14 ms**, total for those aggregate queries **1,121.78 ms**. This is one machine/run measurement, not a production performance guarantee; timings varied across repeated local runs.
