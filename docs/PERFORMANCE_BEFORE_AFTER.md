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

## Latest Phase 8 measurements

| Rows | Generation + insert (s) | Python peak (MiB) | Process RSS peak (MiB) | Summary (ms) | Songs (ms) | Artists (ms) | DB size (MiB) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 25,000 | 3.186 | 4.76 | 61.27 | 61.76 | 71.25 | 55.29 | 18.67 |
| 100,000 | 27.152 | 4.81 | 62.75 | 377.54 | 495.92 | 316.75 | 75.48 |
| 500,000 | 187.436 | 5.16 | 64.38 | 8,956.98 | 2,701.96 | 6,397.45 | 370.27 |

The latest 500k figures compared with the Phase 7 baseline:

| Measurement | Phase 7 baseline | Latest Phase 8 | Change |
|---|---:|---:|---:|
| Generation + insert | 148.383 s | 187.436 s | 26.3% slower |
| Summary query | 12,105 ms | 8,957 ms | 26.0% faster |
| Top songs | 8,614 ms | 2,702 ms | 68.6% faster |
| Top artists | 11,273 ms | 6,397 ms | 43.2% faster |
| Python allocation peak | 4.76 MiB | 5.16 MiB | +0.40 MiB |
| Database size | 302.04 MiB | 370.27 MiB | 22.6% larger |
| Process RSS peak | Not measured | 64.38 MiB | Baseline unavailable |

The 500k summary and artist queries remain well above the aspirational 1,000 ms
and 2,000 ms targets, respectively; songs also exceeds the 2,000 ms target.
The added index improves query latency at a real storage and insertion cost.
No performance target should be considered met solely from these synthetic
measurements.

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
