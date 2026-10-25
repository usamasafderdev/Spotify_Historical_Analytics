# Windows Visual QA Checklist

This checklist requires a normal Windows desktop session. Offscreen Qt tests are not a substitute.

## Prepare

1. Use a Windows 10/11, 64-bit system with the project's supported Python and dependencies installed.
2. From the repository root, run:

   ```powershell
   python -m pip install -e .
   python -m spotify_historical_analytics
   ```

3. Use **Preview synthetic data** to populate a clearly labeled, isolated demo dataset. Confirm the banner says `DEMO / SYNTHETIC MODE` and that the Settings page shows a temporary isolated fixture, not the production database path.

## Window sizes and appearance

Inspect the application at **1366 x 768**, **1600 x 900**, and **1920 x 1080**. At every size, check:

- No solid black rectangles appear behind the logo, subtitle, filter labels, KPI labels/values, chart titles, or chart descriptions.
- Text remains readable over the main, sidebar, and card surfaces; contrast and focus indication are visible.
- Sidebar icons line up vertically and long navigation labels are not clipped.
- Header actions and shared date/chart filters fit or can be reached by scrolling without overlap.
- KPI titles, values, and descriptions wrap without covering adjacent cards.
- Charts resize within their cards; axes, labels, and empty states remain visible.
- Tables resize, preserve readable headers, and expose horizontal/vertical scrolling when content needs it.
- Main content has a working vertical scrollbar at shorter heights; there is no absolute-position overlap.

## Filters, navigation, and data integrity

- Switch among all six navigation pages and verify the active page styling and selected dates persist.
- In an empty production database, verify the displayed start date is January 1, 2017, the end date is today's date, and no rows or chart points are fabricated.
- In demo mode, verify initial dates reflect available synthetic observations; test Apply, All available, Last 7 days, Last 30 days, Last 90 days, and Last year.
- Toggle Daily/Weekly. Confirm rankings, charts, and detail views do not mix chart types. Gaps remain visibly missing.
- Search rapidly in songs, artists, and albums, then change filters while results are loading. Confirm the UI stays responsive and old results do not replace the latest query.
- Open song, artist, and album details and confirm the active date range and chart type apply to their trends. Artist full-credit and album charting-track caveats must remain visible.
- Click **Return to real data** and confirm user-supplied production rows, settings, and filters are restored. Verify imports, backups, and exports are re-enabled only in real mode.

## Import, backup, and exports

- Import an authorized CSV and XLSX test file. Verify progress stages, accepted/rejected/duplicate counts, visible errors, and automatic refresh.
- For a deliberate fatal database failure in a disposable test database, verify rollback leaves no partial batch or rows. Do not run destructive failure injection against customer data.
- Create a database backup and verify it can be opened/restored in a separate disposable database.
- On each ranking page, export CSV and XLSX with a date range and search applied. Compare ranking values with the on-screen table.
- Open CSV in a text editor and Excel; verify metadata, source coverage/attribution, and rankings sections. Open XLSX and verify `Rankings`, `Definitions`, and `Coverage & Sources` worksheets.
- Try an empty filter and verify the export retains definitions and headers but contains zero ranking rows.

## Report the result

Record Windows version, display scaling, app build/commit, resolutions inspected, import source/license identifiers, export formats checked, and any clipping/readability defects. Do not include or redistribute client data in screenshots or test reports without authorization.
