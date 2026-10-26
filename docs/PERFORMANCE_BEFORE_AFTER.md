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

## Phase 9 measurements (2026-10-26)

The baseline was freshly measured using the existing synthetic generator at
25k/100k/500k observations. After the query changes, the same retained databases
were queried again, without rebuilding or adding indexes. Each figure is an
observed run, not a statistical latency guarantee. Cache warmth and host load
were not controlled. Query plans and after figures are retained in
[query-plans-and-after.json](screenshots/phase9/query-plans-and-after.json).

| Rows | Summary before / after (ms) | Songs before / after (ms) | Artists before / after (ms) | Unchanged DB (MiB) |
|---:|---:|---:|---:|---:|
| 25,000 | 30.01 / 34.07 | 57.34 / 70.79 | 36.10 / 41.27 | 18.68 |
| 100,000 | 619.15 / 144.83 | 689.66 / 257.56 | 353.92 / 181.79 | 75.49 |
| 500,000 | 7,887.67 / 881.79 | 2,809.91 / 1,277.12 | 5,828.37 / 853.40 | 370.28 |

SQLite scratch trees now use memory (`temp_store=MEMORY`). Artist attribution
uses a deduplicated materialized track/artist mapping and one chart scan, replacing
the repeated UNION/correlated fallback path. Plans use the existing covering real
analytics index; grouping and DISTINCT scratch trees still exist. No summary cache
or additional persistent index was introduced. The arithmetic oracle verifies
full-credit collaborators, whole-credit fallback, and duplicate mapping rules.

The first complete Phase 9 suite separately measured these figures in a UI-loaded
process. This is not the same-database A/B comparison above:

| Rows | Insert (s) | Summary (ms) | Songs (ms) | Artists (ms) | Peak process RSS (MiB) |
|---:|---:|---:|---:|---:|---:|
| 25,000 | 6.070 | 80.25 | 106.11 | 53.57 | 277.24 |
| 100,000 | 29.794 | 316.50 | 786.02 | 297.77 | 285.26 |
| 500,000 | 179.027 | 1,536.84 | 2,426.74 | 1,468.11 | 344.20 |

Baseline insertion was 2.538 / 24.550 / 168.399 seconds. Insertion has **not**
been shown to improve. Process RSS includes imported UI/test modules and cannot
be compared directly to the baseline-only process (66-68 MiB). Memory scratch
trees also trade RAM for disk latency. The database is still 370.28 MiB at 500k.
Some small-data timings regressed slightly. These results do not establish that
all performance targets are met on client hardware. Fresh final-suite evidence
and its host-load qualifications are in [Phase 9 QA](PHASE_9_ENGINEERING_QA.md).

Dashboard work remains off the GUI thread. Superseded dashboard reads now receive
SQLite progress-handler cancellation in addition to generation guards. A real
QThread regression interrupts a long recursive SQLite query without surfacing an
error; visual automation verifies filter/search transitions and shutdown.
