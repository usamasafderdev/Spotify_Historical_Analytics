> Historical report: the wizard and mandatory manifest described here have been replaced. See [SIMPLE_IMPORT_INTERFACE.md](SIMPLE_IMPORT_INTERFACE.md) for the current workflow.

# Phase 8B — Resumable, Rights-Gated Import Workflow

## Scope

Phase 8B adds an actual Qt import wizard to the existing application. It does
not replace the dashboard, enable research-dataset imports, or certify any
source's legal status. The wizard currently accepts generic CSV/XLSX files
with explicit field mapping; it does not automatically route MGD+ or Dhruvil
files through their source-specific adapters.

## Workflow and persistence

The wizard has 13 user-visible stages: file selection; source identity and
cadence; file detection; schema mapping and staging; market validation; date
and chart validation; stream validation; track/artist/album identity review;
duplicate/conflict review; coverage review; rights evidence review; explicit
confirmation; and transactional import/integrity verification.

CSV input is streamed, and XLSX input uses read-only workbook iteration.
Accepted observations are committed to an independent SQLite staging database
in chunks of 2,000. Rejection counts are aggregated and a maximum of 100
example rows are retained. Sessions persist source fingerprint, column map,
stage, status, and progress checkpoint. A changed file is marked stale and
cannot resume against prior staged data. Startup offers recovery for pending
sessions.

The staging database is located at:

```text
<production database parent parent>\staging\import_sessions.sqlite3
```

It is kept under the per-user application data root in normal application
configuration and is not located in the developer research directory.

## Rights and transaction boundary

A rights manifest must match the exact source name and SHA-256 of the selected
file and identify the dataset/version, reviewer, review time, evidence path,
evidence SHA-256, and explicit `true` values for `acquisition`,
`derived_analytics`, `commercial_use`, and `redistribution`. The import worker
rechecks source and evidence hashes immediately before the transaction. A
checkbox, a source license field, or a manifest assertion is not independent
proof of permission. The software cannot authenticate reviewers or interpret
contracts.

Production records, explicitly supplied artist/album mappings, and recorded
approval metadata are written in one SQLite transaction. Conflicting source
observations or conflicting non-empty artist/album metadata IDs block the
transaction. `PRAGMA integrity_check` runs before commit. Repeating the same
observations in a new session skips matching chart rows rather than adding
their stream values. The production schema is version 2; the new approval
table is created for existing databases without removing existing records.

The legacy metadata-only Settings import is disabled because it bypasses this
workflow. Metadata-only staging is not yet implemented. Album and artist
identity fields are only used when explicitly supplied; the credited artist
string is never split heuristically to invent artist IDs. Multiple explicit
artist IDs do not duplicate chart streams.

## Verification performed in this worktree

- New staging and Qt wizard tests use generated synthetic data and evidence,
  not MGD+ or Dhruvil source records.
- Focused results:

  ```powershell
  python -m pytest -q tests\test_import_sessions.py tests\test_import_wizard.py
  ```

- Full suite: `python -m pytest -q -s` — **106 passed**. The run included the
  25k, 100k, and 500k synthetic benchmarks; recorded results are in
  [PERFORMANCE_BEFORE_AFTER.md](./PERFORMANCE_BEFORE_AFTER.md).
- Compilation: `python -m compileall -q src scripts tests` passed.
- Whitespace validation: `git diff --check` passed.
- Packaged verification: rebuilt with `scripts\build_windows.ps1 -SkipTests`,
  ran `scripts\verify_release.ps1`, and ran the packaged
  `--demo-smoke-test` in an isolated directory. Startup, persistence,
  integrity, export, and synthetic widget checks passed.
- Current executable SHA-256:
  `F5027F776D94CA7E389E04619A37B10F017C01171282143DD6FBF0121FB6F185`.
- The package scan found no SQLite databases, TSV files, MGD+/Dhruvil source
  records, research staging databases, or import-session databases.
- The developer production database was read-only checked at
  `%LOCALAPPDATA%\USMusicChartsAnalytics\database\analytics.db`: 0 chart rows,
  0 synthetic rows, schema version 1. Tests and release smoke checks used
  isolated temporary/build data roots and did not change it.
- Inno Setup 6 is unavailable, so no installer was compiled. Native
  interactive Windows/DPI inspection was not performed.

## Outstanding work

- Add a separate metadata-only staged importer using the same reviewed rights
  workflow.
- Wire supported MGD+ and Dhruvil adapters into the staged import entry point
  only after the exact schema/source version is selected and rights are
  independently established.
- Re-run the existing reproducible 25k/100k/500k analytics benchmarks;
  earlier 500k latency goals were unmet and this workflow does not claim they
  are now met.
- Rebuild and run packaged smoke tests from the current source.
- Perform native Windows visual and DPI checks at 100%, 125%, and 150%.
- Compile and verify the installer if Inno Setup is available.
- Keep all research rows isolated until evidence for intended use is reviewed.

No client-delivery readiness or MGD+/Dhruvil authorization is claimed.
