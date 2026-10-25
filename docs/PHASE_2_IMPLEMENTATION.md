# Phase 2 Dashboard Implementation

## Implemented

- Native PySide6 dashboard with six working sidebar pages and shared chart/date filters.
- Overview KPIs and PyQtGraph streams-over-time and top-10 charts.
- Daily and weekly data are queried independently. Gaps remain missing observations instead of being rendered as zero streams.
- Top Songs page supports title/artist search, top 50/100/200 selection, sortable columns, and double-click detail view with a historical trend.
- Top Artists and Top Albums were expanded in Phase 3; see [PHASE_3_IMPLEMENTATION.md](./PHASE_3_IMPLEMENTATION.md).
- Data Sources & Coverage displays source, chart type, market, row counts, date ranges, annual observation counts, and missing dates between observed dates.
- Settings includes local database location and database backup.
- CSV/XLSX import reports valid, rejected, and duplicate row counts and refreshes the dashboard.
- Synthetic demo data is visibly identified and excluded from real-data charts, rankings, KPIs, and source coverage.

## Data interpretation and limitations

- Streams are sums of user-imported chart observations, not official platform-wide totals.
- Annual and date coverage is observational, not verified complete. The application has no authoritative expected reporting calendar and does not assert licensing or redistribution rights.
- Weekly dates are filtered by the stored `chart_date`; the weekly start/end values are shown as period metadata when available. A weekly total is not prorated into daily values.
- Artist identity/attribution follows the credited artist string in imported rows. Collaborator splitting is not inferred.
- Artist totals can overlap where a charting song is assigned full credit to multiple supplied artist IDs.
- Album totals require user-supplied stable-ID mappings and may overlap across album editions.
- Imports, dashboard aggregations and debounced search queries, and song/artist/album detail queries run in worker threads with worker-owned SQLite connections. Stale dashboard/detail results are discarded.
- Imports expose progress stages and accepted/rejected/duplicate counts; transactions roll back on fatal failures. Cancellation is not available once transactional import begins.
- Date controls default to January 1, 2017 through today when no observations exist, and to actual available chart-date boundaries when data exists. Applying filters with no observations returns empty results rather than silently dropping the date range.
- Synthetic visual QA data now uses an isolated temporary database and is removed when the application closes; it cannot be included in production rankings, backups, or exports.
- Top Songs, Top Artists, and Top Albums can be exported as CSV or XLSX for the active USA/chart/date/search and Top N selection. Excel workbooks contain Rankings, Definitions, and Coverage & Sources sheets. The interface and widgets have automated offscreen tests but still require visual inspection on Windows at common display sizes; see [WINDOWS_VISUAL_QA_CHECKLIST.md](./WINDOWS_VISUAL_QA_CHECKLIST.md).

## Verification

```powershell
python -m pytest -q
$env:QT_QPA_PLATFORM = "offscreen"
python -m spotify_historical_analytics
```

The module launch command is an interactive application and is expected to remain running until its window closes. The pytest UI smoke test creates and exercises a window in offscreen mode without starting a persistent event loop.
