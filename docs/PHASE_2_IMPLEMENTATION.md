# Phase 2 Dashboard Implementation

## Implemented

- Native PySide6 dashboard with six working sidebar pages and shared chart/date filters.
- Overview KPIs and PyQtGraph streams-over-time and top-10 charts.
- Daily and weekly data are queried independently. Gaps remain missing observations instead of being rendered as zero streams.
- Top Songs page supports title/artist search, top 50/100/200 selection, sortable columns, and double-click detail view with a historical trend.
- Top Artists displays aggregates from credited artist strings. Top Albums explains that album metadata is unavailable rather than showing fabricated results.
- Data Sources & Coverage displays source, chart type, market, row counts, date ranges, annual observation counts, and missing dates between observed dates.
- Settings includes local database location and database backup.
- CSV/XLSX import reports valid, rejected, and duplicate row counts and refreshes the dashboard.
- Synthetic demo data is visibly identified and excluded from real-data charts, rankings, KPIs, and source coverage.

## Data interpretation and limitations

- Streams are sums of user-imported chart observations, not official platform-wide totals.
- Annual and date coverage is observational, not verified complete. The application has no authoritative expected reporting calendar and does not assert licensing or redistribution rights.
- Weekly dates are filtered by the stored `chart_date`; the weekly start/end values are shown as period metadata when available. A weekly total is not prorated into daily values.
- Artist identity/attribution follows the credited artist string in imported rows. Collaborator splitting is not inferred.
- The current importer does not populate album metadata. Album ranking remains unavailable until reliable user-supplied mappings are supported.
- Import and analytics refresh execute synchronously in the GUI. Very large files or datasets may temporarily block interaction; background workers and cancelable progress are not implemented.
- The interface and widgets have an automated offscreen smoke test, but still require visual inspection on Windows at common display sizes.

## Verification

```powershell
python -m pytest -q
$env:QT_QPA_PLATFORM = "offscreen"
python -m spotify_historical_analytics
```

The module launch command is an interactive application and is expected to remain running until its window closes. The pytest UI smoke test creates and exercises a window in offscreen mode without starting a persistent event loop.
