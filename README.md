# US Music Charts Analytics

An independent local Windows desktop application for analyzing user-supplied US music chart CSV/XLSX observations. Metrics are derived only from imported rows; they are not official platform totals and do not imply complete historical coverage. The application is not affiliated with or endorsed by Spotify.

Current acceptance: [Phase 10 release acceptance](docs/PHASE_10_RELEASE_ACCEPTANCE.md), [handover checklist](docs/FINAL_CLIENT_HANDOVER_CHECKLIST.md), and [supported data schema](docs/SUPPORTED_DATA_SCHEMA.md). The frozen 0.1.0 installer and local review package are prepared; final client delivery remains blocked by data, clean-machine, human desktop and redistribution acceptance. Earlier engineering evidence remains in [Phase 9 QA](docs/PHASE_9_ENGINEERING_QA.md). Client instructions: [user guide](docs/USER_GUIDE.md).

## Setup

Requires Python 3.12 or newer for source development.

```powershell
python -m pip install -e ".[test,build]"
```

The optional `test` extra provides pytest. The `build` extra provides PyInstaller and Pillow for creating the Windows application icon and executable.

## Launch

```powershell
python -m spotify_historical_analytics
```

## Windows standalone build

On a 64-bit Windows machine with the dependencies installed:

```powershell
.\scripts\build_windows.ps1
```

The script runs the test suite and syntax compilation, generates the original application icon and version resource, builds a windowed PyInstaller onedir application, launches an offscreen packaged-app smoke test, and records a SHA-256 hash. Output is written to `dist\USMusicChartsAnalytics\`. Build/test datasets, databases, and temporary output are not bundled.

To create the per-user installer, install Inno Setup 6 from [jrsoftware.org/isinfo.php](https://jrsoftware.org/isinfo.php), then run:

```powershell
.\scripts\build_installer.ps1
```

The installer target is `dist\installer\US-Music-Charts-Analytics-Setup.exe`. If Inno Setup is absent, the script fails with its official installation location; the installer must not be described as compiled. The build is unsigned unless a release owner separately adds and verifies an authorized signing process.

## Local data and recovery

The Windows application stores writable state under `%LOCALAPPDATA%\USMusicChartsAnalytics\`:

- `database\analytics.db` — SQLite chart and metadata records.
- `logs\` — rotating local diagnostic log.
- `backups\` — suggested location for manual database backups.
- `exports\` — suggested location for exported reports.
- `config\settings.json` — last-used import and export folders.

The application and installer do not place the writable database in the installation directory, and uninstall does not remove the separate Local AppData directory. On first launch, if a development database is detected, the application asks whether to copy it. The original is retained, the destination is never overwritten, and a failed copy leaves the source unchanged.

Use **Settings → Create database backup** before replacing or restoring data. Backups are not overwritten. Store an additional copy outside the computer for disaster recovery. No cloud sync is performed.

Install a newer per-user build over the existing application to update it. The data folder is independent of the installation directory and should remain intact. Verify a backup before upgrading important client records.

## Dashboard

- Overview KPIs and interactive PyQtGraph charts for real imported daily or weekly observations.
- Shared chart-type and inclusive date filters, with last 7/30/90 days and last-year presets.
- Top Songs rankings with search, sorting, top 50/100/200 selection, and a double-click detail view.
- Top Artists rankings with full-credit stable-ID attribution, exact-string fallback, search, details, and a trend chart.
- Top Albums rankings from exact user-supplied stable track/album ID mappings, with track lists and trends.
- Source inventory, annual observation counts, missing-date inspection, and local database backup.
- Data Sources & Coverage reports observed rows, valid stream counts, unique track IDs, exact artist/album mapping coverage, rights status, and import status for 2017–2026. Research staging is explicitly separate and is not queried by the application.
- CSV/XLSX exports for filtered Top Songs, Top Artists, and Top Albums rankings. Excel files contain separate Rankings, Definitions, and Coverage & Sources sheets.
- One **Import Dataset** dialog for CSV, XLSX, and supported CSV.GZ tables: automatic schema detection, coverage and USA record preview, validation warnings, progress, safe cancellation, backups, duplicate prevention, transactional writes, and SQLite integrity checks. MGD+ and Dhruvil chart schemas are recognized automatically; unknown columns can be mapped inside the same dialog. No JSON permission file or multi-page wizard is required.
- Artist/album associations are accepted only from explicitly supplied stable IDs and names in a validated chart-data import. The separate legacy metadata-only control stays disabled; use the optional chart/metadata mappings in Import Dataset.
- Background dashboard search and song/artist/album detail queries; stale responses are discarded after newer filters.
- Synthetic demo preview uses a temporary, isolated fixture database with multi-year daily/weekly observations, intentionally missing dates, collaborations, and labeled synthetic metadata. Returning to real data does not modify the production database.
- On a first run with no imported chart records, Overview shows “No historical chart data is loaded yet.” with actions to import a dataset, preview the synthetic dashboard, or inspect data sources. Empty production data is shown as an explicit empty state rather than zero-valued KPIs.

For an automated widget-level demo launch check, use `--demo-smoke-test`. This opens the same isolated synthetic dashboard and exits with a non-zero code if the KPI cards, song/artist/album tables, or charts do not populate. Set `SPOTIFY_ANALYTICS_DATA_DIR` to a disposable folder when running this check so it does not touch the regular per-user database.

Metadata support is limited to user-supplied data. No restricted Spotify metadata is fetched or scraped. Album totals are labeled **Album charting-track streams** and do not represent comprehensive platform album totals.

The initial date window begins at the earliest imported date when data exists, otherwise January 1, 2017. The end date defaults to the latest imported date or the current date and cannot be set beyond the current date.

Exports use the current USA chart type, inclusive date range, search, and Top 50/100/200 selection. CSV exports include report metadata and source-coverage sections before the rankings section. XLSX exports include dedicated rankings, definitions, and source-coverage worksheets. Only the selected top-N rows are exported.

**Commercial-use caution:** Spotify's Developer Policy and Developer Terms restrict certain analysis and commercial uses of Spotify Content or the Spotify Platform. User-supplied files do not automatically confer rights to use, analyze, or redistribute their contents. Review [docs/DATA_ACQUISITION_STATUS.md](docs/DATA_ACQUISITION_STATUS.md) before commercial use. This application is not affiliated with or endorsed by Spotify.

## Importing local files

Click **Import Dataset ? Browse Files**, select a CSV, XLSX, or CSV.GZ file, and review its source name, cadence, valid USA records, date coverage, and warnings. Then click **Import Dataset**. Compatible schemas map automatically. For an unknown schema, expand **Show column mapping (optional)**, map the five required fields, and click **Validate Mapping**. Daily and weekly records remain separate; missing weekly boundaries are rejected. A backup is saved before production writes.

Only explicitly selected files are imported. Source terms still apply, and local import does not grant commercial or redistribution rights. Existing research staging databases are never automatically promoted or bundled. There is no standalone Zenodo weekly adapter; compatible weekly tables require explicit date boundaries.

Implementation details, tests, and rendered evidence: [docs/SIMPLE_IMPORT_INTERFACE.md](docs/SIMPLE_IMPORT_INTERFACE.md).

## Tests

```powershell
python -m pytest -q
```

The tests include an offscreen Qt widget/navigation smoke test. It does not replace visual verification in a normal Windows desktop session.

## Optional historical dataset research

The client production database and Windows EXE do not require KaggleHub. To audit the two candidate Kaggle archives in a separate research directory, install the optional tools and run:

```powershell
python -m pip install -e ".[research,test]"
python scripts/download_historical_datasets.py --download --research-root "D:\Spotify-Dataset-Research"
```

The workflow pins the reviewed dataset versions, reuses local cache entries, processes supported tabular files in chunks, and writes audit/rejection/coverage reports plus a separate research SQLite staging database. It does not assume that the Kaggle sources are USA-only or approved for commercial use, and it does not import research rows into the application's database or package them into the EXE. The source-rights state defaults to `UNVERIFIED`; an archive license, download, user upload, or attribution entry alone is not production approval.

If Kaggle requires authentication, use KaggleHub's local documented login or secure credential configuration. Never put API tokens in source code, arguments, or logs. Do not bypass filesystem permissions: specify a writable `--research-root` if `D:\Spotify-Dataset-Research` cannot be created. See [docs/PHASE_6_IMPLEMENTATION.md](docs/PHASE_6_IMPLEMENTATION.md), [docs/DATASET_DISCOVERY_REPORT.md](docs/DATASET_DISCOVERY_REPORT.md), [docs/DATASET_SOURCE_COMPARISON.md](docs/DATASET_SOURCE_COMPARISON.md), [docs/HISTORICAL_DATA_COVERAGE.md](docs/HISTORICAL_DATA_COVERAGE.md), [docs/DATA_PERMISSION_STATUS.md](docs/DATA_PERMISSION_STATUS.md), and [docs/DATA_IMPORT_INSTRUCTIONS.md](docs/DATA_IMPORT_INSTRUCTIONS.md).

Phase 6B adds a separate, checksum-reconciled compact staging workflow and an in-place CRC/schema audit for the Zenodo MGD+ research archive; neither changes or imports production data. The checked-in audit scripts are [scripts/compact_research_staging.py](scripts/compact_research_staging.py), [scripts/audit_mgdplus_archive.py](scripts/audit_mgdplus_archive.py), and the conservative unversioned Kaggle preflight in [scripts/download_historical_datasets.py](scripts/download_historical_datasets.py). The measured results, storage boundary, and remaining year gaps are documented in [docs/PHASE_6B_RESULTS.md](docs/PHASE_6B_RESULTS.md), [docs/STAGING_STORAGE_AUDIT.md](docs/STAGING_STORAGE_AUDIT.md), and [docs/MISSING_YEARS_PLAN.md](docs/MISSING_YEARS_PLAN.md). The updated archive validation and Dhruvil comparison are in [docs/MGDPLUS_VALIDATION_REPORT.md](docs/MGDPLUS_VALIDATION_REPORT.md) and [docs/MGDPLUS_COMPARISON_REPORT.md](docs/MGDPLUS_COMPARISON_REPORT.md). Research datasets and generated reports remain outside Git and the application database.

Phase 7 adds read-only chunked adapters in `spotify_historical_analytics.source_adapters` for the verified MGD+ TSV and Dhruvil CSV schemas. It also records the rights scopes and evidence digest required by the research staging approval gate. These adapters do not import data. See [docs/PHASE_7_IMPLEMENTATION.md](docs/PHASE_7_IMPLEMENTATION.md), [docs/DATA_IMPORT_ACCEPTANCE.md](docs/DATA_IMPORT_ACCEPTANCE.md), [docs/ARTIST_MAPPING_VALIDATION.md](docs/ARTIST_MAPPING_VALIDATION.md), and [docs/HISTORICAL_DATA_GAPS.md](docs/HISTORICAL_DATA_GAPS.md). Rights remain unverified; this phase does not indicate production or client delivery readiness.

Phase 8 optimized repeated summary scanning and expanded query-plan tests. The later 13-stage wizard has been replaced by the single local-file import dialog documented in [docs/SIMPLE_IMPORT_INTERFACE.md](docs/SIMPLE_IMPORT_INTERFACE.md). Source permissions and research-data redistribution are not inferred from a successful local import. Native desktop/DPI review, signing, installer availability, and performance limitations remain separately documented in the release and performance checklists.


See [docs/PHASE_2_IMPLEMENTATION.md](docs/PHASE_2_IMPLEMENTATION.md) for behavior and limitations.
For accepted metadata columns and identity rules, see [docs/METADATA_IMPORT_GUIDE.md](docs/METADATA_IMPORT_GUIDE.md).
For Phase 3 schema, analytics, and performance details, see [docs/PHASE_3_IMPLEMENTATION.md](docs/PHASE_3_IMPLEMENTATION.md).
For Phase 4 behavior and limitations, see [docs/PHASE_4_IMPLEMENTATION.md](docs/PHASE_4_IMPLEMENTATION.md).
For source and legal-readiness status, see [docs/DATA_ACQUISITION_STATUS.md](docs/DATA_ACQUISITION_STATUS.md).
For manual desktop verification, follow [docs/WINDOWS_VISUAL_QA_CHECKLIST.md](docs/WINDOWS_VISUAL_QA_CHECKLIST.md).
For Windows build and release status, see [docs/PHASE_5_RELEASE_PREPARATION.md](docs/PHASE_5_RELEASE_PREPARATION.md).
For installation and data migration, see [docs/WINDOWS_INSTALLATION_GUIDE.md](docs/WINDOWS_INSTALLATION_GUIDE.md).
For redistribution obligations, see [docs/DEPENDENCY_LICENSES.md](docs/DEPENDENCY_LICENSES.md).
