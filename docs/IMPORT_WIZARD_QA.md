# Import Wizard QA

## Current behavior verified

The application currently opens a file dialog for CSV/XLSX chart data and sends the import to a `QThread` worker. The worker opens its own `DatabaseManager`, calls the existing importer, and closes its own DB connection. The importer wraps source, batch, and chart-record writes in a database transaction, reports accepted/rejected/duplicate counts, and rolls back on SQL errors. Metadata imports have a separate preview and mapping dialog.

Automated tests cover source schema handling at the parser level, malformed dates/streams, non-US data, duplicate handling, transaction rollback, metadata mappings, worker lifecycle, export consistency, and package export smoke behavior.

## Phase 8 requested workflow status

The persisted 13-stage GUI wizard is **not implemented**. There is no GUI workflow that captures and persists each stage, stages raw file validation before production, or connects the MGD+/Dhruvil adapters to a stage database.

| Stage | Current state |
|---|---|
| Select data file | Existing file picker for CSV/XLSX |
| Identify source | Filename/source label and user-entered license note |
| Inspect format / preview schema | Metadata has preview; chart data lacks a guided preview wizard |
| Select USA records | Importer rejects explicit non-US rows; missing region currently defaults to selected country |
| Validate dates/chart types | Parser validation and selected chart type checks |
| Validate streaming metrics | Parser rejects missing/non-positive streams |
| Validate IDs/mappings | Stable metadata importer exists; chart import does not require stable IDs |
| Detect duplicates | Exact duplicate records skipped; no first-class conflicting-observation review |
| Review coverage | Coverage page reports imported history after import, not a pre-import candidate report |
| Review permission evidence | Not part of the manual import GUI |
| Confirm authorized import | Existing direct manual import confirms only through file selection, not a rights review |
| Transactional import | Implemented for existing CSV/XLSX import |
| Verify results | Import counts and database API checks exist; no unified persisted report |

## Rights boundary

The manual file-import UI does not independently prove rights and must not label a user-entered source/license string as APPROVED. The research-staging `source_rights` approval gate remains separate and requires a dataset/version plus documentary evidence and declared scopes; the application cannot verify the legal effect of that evidence. Current research data remains unapproved and has not been imported.

## Required follow-up for acceptance

- Build a persisted import job/stage model and a wizard with explicit, auditable transitions.
- Make file reading chunked and provide bounded previews/progress without loading multi-gigabyte sources fully into memory.
- Connect source adapters to isolated staging, not the production database.
- Show duplicates/conflicts, market/date/chart/stream/identity validation, and coverage before approval.
- Require an independently reviewed source/version approval record before transactional production import.
- Add GUI integration tests for wizard navigation, worker cleanup, rollback, repeated import, and permission-gate rejection.
