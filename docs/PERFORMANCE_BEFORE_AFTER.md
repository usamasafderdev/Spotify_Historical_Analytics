# Performance Before / After

## Method and limitations

Measurements are from the reproducible synthetic database test
`tests/test_performance.py`, using 25k, 100k, and 500k generated chart rows.
Rows are generated in 5,000-row batches and inserted using the normal
application schema and indexes. Insert duration includes synthetic row
generation and batch inserts. Query times are local wall-clock timings for
summary, top songs, and top artists. `tracemalloc` records Python allocations;
process RSS was sampled in a background thread with `psutil`.

These figures are synthetic benchmarks, not a guarantee of client-device
performance. The generated data has a deliberately repetitive date range and
artist distribution, with unique track IDs. Do not extrapolate it directly to
all authorized datasets.

## Latest Phase 8B full-suite measurements

| Rows | Generation + insert (s) | Python peak (MiB) | Process RSS peak (MiB) | Summary (ms) | Songs (ms) | Artists (ms) | DB size (MiB) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 25,000 | 3.095 | 4.76 | 226.28 | 34.40 | 66.78 | 37.40 | 18.68 |
| 100,000 | 24.196 | 4.80 | 229.66 | 283.31 | 269.73 | 173.83 | 75.49 |
| 500,000 | 112.912 | 5.00 | 228.18 | 5,083.78 | 1,951.11 | 4,030.18 | 370.28 |

These measurements were printed during a full pytest process. Its process RSS
includes imported test/UI modules and is not comparable with an isolated
benchmark's RSS. Earlier full-suite runs on this worktree also produced
different 500k timings, so these are reported observations rather than a
controlled before/after claim. The 500k summary and artist queries remain well
above the aspirational 1,000 ms and 2,000 ms targets, respectively. Songs was
1,951 ms in this run, which is not sufficient evidence to declare the 2,000 ms
target met. No performance target should be considered met solely from these
synthetic measurements.

## Query-plan evidence

On synthetic records, the baseline `EXPLAIN QUERY PLAN` showed:

- Summary used `idx_chart_records_artist` for `(country, chart_type)` but
  required temporary B-trees for distinct aggregates.
- Songs used a non-covering chart-record index and temporary B-trees for
  grouping, distinct chart dates, and output ordering.
- Artists used a compound query, a deduplicating mapping subquery, correlated
  mapping lookups, and temporary B-trees for grouping and distinct counts.

An isolated 100k-row index experiment showed the partial index reduced summary
from 317 ms to 161 ms, songs from 452 ms to 413 ms, and artists from 320 ms to
262 ms; the database grew from 49.75 MB to 59.24 MB. The full synthetic
benchmark selected `idx_chart_records_market_type_date` for its date-range
plan. A separate summary-plan regression asserts use of
`idx_chart_records_real_analytics`.

## Remaining optimization work

- Profile realistic source/track repetition and 500k+ authorized-like data
  distributions before choosing further index changes.
- Optimize summary and artist aggregation without changing exact track, artist,
  or date semantics.
- Reassess whether the current index's write-time and storage costs are
  acceptable for expected client hardware.
- Keep expensive work on background workers; query benchmarks do not establish
  interactive UI responsiveness.
- Repeat performance and interactive checks on representative Windows 10/11
  client hardware before delivery.
