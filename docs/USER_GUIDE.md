# US Music Charts Analytics user guide

Version 0.1.0, Windows x64. This release candidate analyzes locally supplied US chart observations. Historical datasets are not included. Client delivery remains subject to the data decision and release checks in [release acceptance](PHASE_10_RELEASE_ACCEPTANCE.md).

## Install and launch

Run the approved `US-Music-Charts-Analytics-Setup.exe`. Installation is per Windows user; a Start Menu shortcut is created and a Desktop shortcut is optional. Launch **US Music Charts Analytics** from Start. Python, VS Code, Excel, Spotify credentials, and an internet connection are not needed for local analysis. For the portable distribution, retain the entire `USMusicChartsAnalytics` folder, including `_internal`; launch its EXE.

The current build is unsigned. Follow your organization's software approval process if Windows blocks it. Do not disable security protections. Back up existing records before installing an update.

## Navigate and filter

The sidebar has seven pages: Overview, Top Songs, Top Artists, Top Albums, Data Sources & Coverage, Data Management / Import, and Settings. Scroll the content area when controls or charts extend below the window.

Choose **Daily** or **Weekly**, set From and To, then click **Apply**. Both dates are included. Presets select recent periods relative to the available data. **All available** restores the observed date range. Daily and weekly records are analyzed separately. An empty period means no matching imported observations; missing days are not converted to zero streams.

- **Overview:** chart-stream sum, charting-song count, distinct credited strings, observed dates, coverage, and charts. Hover chart points for observation values; use the chart menu and mouse controls to inspect a range.
- **Top Songs:** search names or credits, select Top 50/100/200, and click a table heading to sort. Double-click a row for its observed history and details.
- **Top Artists:** streams from charting songs attributed to supplied stable artist IDs. Each mapped collaborator receives full credit, so totals across artists can overlap. Unresolved credits remain whole strings; names are not guessed or split.
- **Top Albums:** streams from charting tracks with supplied stable track-to-album ID mappings. Different album editions remain separate. Without those mappings, album results stay empty.
- **Data Sources & Coverage:** inspect actual imported sources, dates, mapping coverage, and quality/rights status. Observed coverage is not a certification of completeness.

All streaming metrics refer to imported chart observations. They are not all-platform Spotify totals. See [metric definitions](METRIC_DEFINITIONS.md).

## Import a dataset

Click **Import Dataset**, browse to a CSV, supported CSV.GZ, or XLSX file, and wait for validation. Known compatible, MGD+, and Dhruvil schemas map automatically. For other tabular schemas, expand **Show column mapping (optional)** and map the required date, track, credited artist, streams, and country fields, then validate. Supply weekly boundaries for weekly observations. Review detected cadence, date coverage, USA counts, rejections, duplicates, and warnings before clicking **Import Dataset**.

Validation runs in the background with progress. Cancellation stops safely; the final production write is transactional. Repeated observations are skipped, conflicting values block import, and the existing database is backed up before changes. Invalid rows are reported rather than invented or repaired silently. Very large imports can take several minutes and require additional space for staging and backup.

There is one import dialog, no JSON rights manifest, and no multi-page questionnaire. Import only files you are permitted to use. Importing or entering a source note does not grant commercial or redistribution rights. Research candidates are not imported automatically.

See [supported data schema](SUPPORTED_DATA_SCHEMA.md) for required columns, weekly periods, exact artist/album associations, and an explicitly synthetic example.

## Export a ranking

On a ranking page choose **Export**, then select CSV or XLSX using the filename extension. The report follows the active chart type, inclusive dates, search, and Top-N limit. CSV uses UTF-8 with a byte-order mark. Excel includes Rankings, Definitions, and Coverage & Sources sheets; streaming counts remain numbers. Formula-like untrusted text is escaped. Choose a writable destination and wait for the success message. A failed write retains an existing report.

## Preview synthetic data

Click **Preview Demo Dashboard** to explore generated fixtures. The title, banner, detail dialogs, and exported definitions identify **DEMO / SYNTHETIC DATA**. Demo exports are available for demonstration. These values are not real historical observations. **Return to real data** restores your normal database. Preview does not insert synthetic rows into it. Return to real data before creating a backup; backups use the normal database.

## Settings and backup

Settings provides data/log folder shortcuts and **Create database backup**. Choose a new filename; existing backups are not overwritten. Keep an additional copy off the computer. Import/export folders are remembered. Data normally lives under `%LOCALAPPDATA%\USMusicChartsAnalytics\`, separately from the program. Upgrade and uninstall preserve that directory. Restore is a support procedure performed with every app instance closed, rather than a restore button.

## Update the application

Create and verify a database backup, close every application window, then run the approved newer installer for the same Windows account. Keep the default existing installation location. User data is separate from installed files and should be retained. Reopen the app and verify your source counts, filters, and a report before continuing work. Keep the backup until the update is accepted. Uninstalling the program also retains the separate user data directory.

## Troubleshooting and limitations

- Empty dashboard: import a permitted dataset or use synthetic preview. A fresh real database is intentionally empty.
- Missing albums/artists: supply valid stable ID associations; display names alone do not establish mappings.
- Rejected file: inspect validation warnings. Re-export corrupt Excel/compressed files, use UTF-8 CSV, and provide valid dates, USA country values, and whole nonnegative stream counts.
- File changed after validation: select and validate it again before importing.
- Date error: choose a start date on or before the end date.
- Export/backup error: check destination permissions and free disk space, then choose another folder.
- Already running: use the existing application window; one instance owns each data directory.
- Unexpected failure: review local logs from Settings and provide the relevant diagnostics to support, excluding sensitive information.

There is no verified complete 2017-2026 dataset in this release. Research candidates, sampled weekly archives, and missing metadata are not complete daily history. The client is still deciding between bundled historical data and client-supplied imports; source approval and actual coverage must be resolved before final delivery.
