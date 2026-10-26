# Research Data Import Instructions

## Install optional research tools

The desktop application does not require KaggleHub. For research ingestion only:

```powershell
python -m pip install -e ".[research,test]"
```

The optional `research` extra includes KaggleHub, PyArrow, psutil, and tqdm. Core Qt dependencies are not upgraded by the ingestion command beyond normal project constraints.

## Download and audit

```powershell
python scripts/download_historical_datasets.py --download --research-root "D:\Spotify-Dataset-Research" --chunk-size 50000
python scripts/download_historical_datasets.py --audit-only --research-root "D:\Spotify-Dataset-Research" --chunk-size 50000
```

The downloader pins the two source versions reviewed in `DATASET_SOURCE_COMPARISON.md`, uses separate KaggleHub cache roots, reuses completed files, avoids force download, and skips detected partial transfers. It does not copy the archive into the production database or EXE. If Kaggle requires sign-in, use the documented local KaggleHub login or a secure credential store. Never place tokens in command-line arguments or source files.

The research root must be writable and have enough free space for the source archives and extracted cache. Do not bypass filesystem permissions. Pass another explicit `--research-root` when the suggested root is unavailable.

On the current development machine `D:\` is not writable for this user. The run therefore uses the writable sibling directory `D:\Study Material\University\Spotify-Dataset-Research`; its actual report and source paths are recorded in the current audit output.

The audited CSV generated a 13,912,154,112-byte staging database because rejected source rows are retained with reasons and raw JSON. Check available disk space before processing large files; the figure is specific to this file and schema.

## Staging and audit outputs

The SQLite staging database lives at `staging\research_staging.sqlite`, separate from `%LOCALAPPDATA%\USMusicChartsAnalytics\database\analytics.db`. The audit writes `dataset_inventory.csv`, `coverage_by_year.csv`, `coverage_by_month.csv`, `missing_dates.csv`, `source_overlap.csv`, `data_conflicts.csv`, `import_validation.json`, `historical_coverage.md`, and `deduplication_summary.md` under `reports\`. Per-file inventory records include measured processing seconds and sampled peak process RSS when row processing is supported; the report aggregations stream from SQLite instead of loading every staged record into memory.

CSV and CSV.GZ, Parquet, XLSX/XLSM, and JSONL chart tables are processed in configured row batches. Original source files are read-only inputs. Validated US observations and rejected rows with reasons are written to separate staging tables. A completed file checksum and row numbers make reprocessing idempotent; a failed/incomplete file is restarted without doubling staged rows.

Archives are inventoried and CRC-checked without a second extracted copy. Arbitrary JSON arrays, SQLite dataset contents, and archive-contained CSV rows are not currently normalized; use the inventory to identify them and do not treat them as imported observations.

## Production transfer

No research row is production data by default. First obtain and review written legal/platform permission for the exact source version. Prepare the exact-version approval JSON with `dataset_id`, `dataset_version`, `reviewed_by`, `reviewed_at`, `evidence_path`, and optional notes. Then use `approve_source_rights()` and the controlled `production_import_records()` gate from a separately reviewed operator workflow.

This first implementation does not expose production transfer in the GUI or CLI, and the approval-record function is not a legal approval mechanism. Song-only US Top 200 daily/weekly records with actual stream counts are the only currently compatible production rows; weekly transfer additionally requires explicit week start and end dates. Viral charts and artist/album metrics remain staged. Review sample counts and duplicate/conflict reports before any approved transfer.
