# Phase 4: UI Refinement, Exports, and Client-Readiness QA

## Implemented in this iteration

- Scoped the dark theme so labels use transparent backgrounds, with explicit card, navigation, table, input, empty-state, and focus styling. Sidebar navigation icons use a fixed-width aligned column.
- Set the no-data date default to January 1, 2017 through the current date. With data, the controls initially show imported date boundaries. Dates are capped at today, while pre-2017 imported records remain selectable and are identified in the start-date tooltip. Reset means all available records; applying a date range retains that range even when no rows match.
- Wrapped the main content in a resizable scroll area, retained Qt layout-based resizing, and set a 1120 x 700 minimum size. The requested 1366 x 768, 1600 x 900, and 1920 x 1080 sizes have offscreen geometry coverage but have not been visually inspected on a normal Windows desktop.
- Added CSV and XLSX exports for Top Songs, Top Artists, and Top Albums. Exports use the active market (US), chart type, inclusive date range, search string, and selected Top 50/100/200 limit. Exported ranks and totals come from the same database aggregations as the rankings.
- CSV contains report metadata, source-coverage rows, and a Rankings section. XLSX includes `Rankings`, `Definitions`, and `Coverage & Sources` worksheets with styled headers, autofilters, and frozen header rows. Excel is not required. Values that could be interpreted as spreadsheet formulas are escaped as text.
- Moved debounced dashboard searches and song, artist, and album detail/trend/track queries to workers that open their own database connection. Generation checks discard stale results. The UI thread owns all widget updates.
- Added import progress stages for opening, reading, row validation/import, and committed completion. Accepted, rejected, and duplicate counts remain explicit. Imports remain atomic, and cannot be canceled after transaction processing begins; the progress dialog says so.
- Changed the demo preview to use a temporary, isolated SQLite database. The generated fixture includes 2017–2024 daily and weekly records, multiple tracks/artists/albums, full-credit collaborations, alternate album editions, unmapped tracks, and intentionally missing chart dates. Demo import, backup, and export controls are disabled in preview mode. The generated fixture can be reset with `DatabaseManager.remove_demo_dataset()` and is deleted when the window closes.
- Reserved the `DEMO / SYNTHETIC` source name for generated demo fixtures and closed the SQLite backup connection after copying.

## Export interpretation

- The export is limited to the selected Top N ranking size, and that limit is recorded in report metadata. Search affects which rows qualify before ranking; the default ranking order remains metric-descending, matching the ranking query.
- Song metrics are total chart streams. Artist metrics follow the full-credit stable-ID policy and may overlap across collaborators. Album metrics are **Album charting-track streams**, not comprehensive platform album totals; album editions remain distinct.
- Source coverage is observational and does not establish source completeness. Only non-demo US sources overlapping the selected interval are listed. The included license/attribution note is the stored user-entered note, not a rights determination.
- Empty exports retain metadata and headers but have zero ranking rows.

## Verification

Run:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m pytest -q
git diff --check
```

The automated suite validates all six category/format combinations, filter/search and source metadata, empty exports, spreadsheet formula escaping, date defaults/presets, navigation/filter persistence, isolated demo data, stale dashboard results, detail workers, imports, migrations, backups, and the existing 25,000-row synthetic benchmark.

Offscreen rendering does not prove visual quality on Windows. Follow [WINDOWS_VISUAL_QA_CHECKLIST.md](./WINDOWS_VISUAL_QA_CHECKLIST.md) before client delivery.

## Known limitations / blockers

- A normal Windows visual review at the required resolutions has not been performed in this environment.
- No real USA historical chart years or source licenses have been confirmed for client delivery. See [DATA_ACQUISITION_STATUS.md](./DATA_ACQUISITION_STATUS.md).
- Spotify developer terms may prohibit some derived analysis of Spotify Content and impose commercial-use restrictions. The client's intended source, analytics, and commercial delivery require legal/platform permission review; a user-supplied file or license note alone does not resolve this.
- Exports are capped by the Top 50/100/200 selector; exporting an unlimited full ranking is not supported.
- Export and import progress is shown without cancellation. Imports are transactionally safe, but cannot be interrupted during the transaction.
- Search/detail work runs in background threads but still materializes the selected ranking (up to 200 rows) for the UI. Real client-scale latency must be measured on the authorized production dataset.
- No packaging, signing, install/uninstall, or customer-environment acceptance work was performed.
