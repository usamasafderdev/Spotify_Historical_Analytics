# Windows Release QA Checklist

Use a clean Windows 10/11 x64 VM or a separately documented Windows test account. Record OS build, display scale, app version, artifact SHA-256, tester, date, and results. Do not mark clean-machine checks complete from an offscreen or developer-only run.

## Build and security

- [ ] Run `python -m pytest -q`.
- [ ] Run `python -m compileall -q src tests`.
- [ ] Run `git diff --check`.
- [ ] Build with `scripts/build_windows.ps1`; retain command output and hashes.
- [ ] Scan/approve artifacts using the organization's approved endpoint security process; do not add exclusions or disable Defender.
- [ ] Confirm no historical data, credentials, test database, temporary DB, or development configuration is inside `dist`.
- [ ] Confirm product branding is independent and publisher signature status is reported accurately.

## Packaged first launch and user data

- [ ] Launch the packaged EXE from a path containing spaces and a non-ASCII character.
- [ ] Verify the empty dashboard opens without Python or network access.
- [ ] Verify the import button, Data Sources & Coverage navigation, and synthetic preview are clearly available.
- [ ] Confirm no synthetic preview data appears in production calculations unless preview is explicitly selected.
- [ ] Verify directories are created under `%LOCALAPPDATA%\USMusicChartsAnalytics\`.
- [ ] Import an authorized small fixture, close and restart, and confirm the records remain.
- [ ] Run two instances and confirm the second cannot open the same data store.
- [ ] Confirm readable log files are present and user dialogs do not display a traceback.
- [ ] Test legacy database prompt choices and verify the source is retained and destination is not overwritten.

## UI, scaling, import, export

- [ ] Check 1366×768, 1600×900, and 1920×1080 at 100%, 125%, and 150% scaling.
- [ ] Review overview, songs, artists, albums, coverage, settings, all empty states, and dialogs.
- [ ] Import authorized CSV and XLSX samples; check duplicates, rejected rows, progress, and rollback on an invalid file.
- [ ] Export songs, artists, and albums to CSV and XLSX with active date/chart/search/Top-N filters.
- [ ] Verify source/coverage/metric metadata, formula safety, Unicode file names, empty results, and an invalid destination.
- [ ] Open XLSX with a compatible spreadsheet viewer; Microsoft Excel must not be required by the app.
- [ ] Verify charts, date filters, navigation, and responsiveness while queries/imports run.

## Installer (only after compilation)

- [ ] Compile with Inno Setup 6 and record the exact compiler version.
- [ ] Verify setup file name, x64 architecture, app icon, version, and SHA-256.
- [ ] Install per-user without unnecessary elevation; check Start Menu shortcut and optional Desktop shortcut.
- [ ] Launch installed app, navigate pages, import/export, and restart.
- [ ] Upgrade over the existing version and confirm database and settings persist.
- [ ] Uninstall and verify application files/shortcuts are removed while Local AppData database, logs, settings, and backups remain.
- [ ] Reinstall and verify prior records remain accessible.

## Release gates still requiring owner sign-off

- [ ] Legal/platform review approves the exact historical source, derived analysis, commercialization, exports, and redistribution.
- [ ] Exact source years, market semantics, completeness, provenance, corrections, and metadata gaps are validated.
- [ ] Qt and other bundled dependency licenses/notices are reviewed; any required LGPL compliance materials are supplied.
- [ ] Code signing is added and verified, or unsigned status and SmartScreen behavior are accepted.
- [ ] Client acceptance and final historical data verification are complete.
