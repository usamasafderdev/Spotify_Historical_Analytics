# Phase 8 Implementation

## Implemented in this iteration

- Consolidated summary totals and date bounds into one aggregate SELECT, eliminating a repeated full filtered scan.
- Replaced list membership in missing-date detection with a set, making date candidate membership checks constant-time.
- Added a partial covering index for non-demo analytics queries. Existing records are preserved; SQLite creates the index during normal schema initialization.
- Removed `COUNT(DISTINCT c.id)` from artist and album appearance aggregation where each source chart row can occur at most once within a group. Artist mappings are deduplicated before joins and track-to-album IDs are unique per edition, so each joined row has a distinct primary-key ID in the grouping. Existing attribution, appearance totals, and stream sums remain covered by regression tests.
- Avoided a second redundant overview summary query. The dashboard worker uses the active-dataset summary and the inventory's real/demo row counts instead of running a second summary that combined real and synthetic observations.
- Extended the widget-level synthetic UI test to open and close song, artist, and album detail dialogs using actual isolated demo-database results.
- Added a SQLite query-plan regression test that verifies one summary SELECT and use of the partial covering index.

## Measured performance and limits

See [PERFORMANCE_BEFORE_AFTER.md](./PERFORMANCE_BEFORE_AFTER.md). The index improves ranking/query latency but increases database size and import cost. At 500,000 rows, the measured summary and artist targets are not met. These measurements use synthetic SQLite rows and are not client workload guarantees.

## GUI inspection boundary

Offscreen Qt widget tests cover navigation, empty state, demo population, daily/weekly selection, date/search filters, table sorting, and detail-dialog rendering. No native Windows desktop automation/screenshot tool was available in this session. A normal app process launch and offscreen screenshots are not equivalent to visually reviewing an interactive desktop window or changing Windows DPI scaling. See [GUI_AGENT_INSPECTION.md](./GUI_AGENT_INSPECTION.md).

The 1366×768 offscreen inspection identified tofu sidebar glyphs, redundant
row-number headers, and clipped coverage-table columns. The sidebar now uses
plain-text markers, ranking/coverage tables hide the redundant row header, and
coverage columns size to content with horizontal scrolling. Focused UI tests
cover the resulting widget configuration. Native Windows visuals and DPI
scaling are still unverified.

## Staged GUI import status

The requested 13-stage, persisted guided import wizard is **not complete**. Current CSV/XLSX imports continue to use the existing background worker and transaction-safe import functions. The source adapters are read-only and are not wired to a GUI stage database or approval workflow. Current manual file import does not independently verify rights; provenance remains user-supplied and unverified. Research-source/version production imports continue to use the explicit `source_rights` gate in the separate research pipeline. No MGD+ or Dhruvil data was imported.

See [IMPORT_WIZARD_QA.md](./IMPORT_WIZARD_QA.md) for verified behavior and blockers.

## Release status

The Phase 8 Windows x64 EXE was rebuilt from the current source. The build
script's offscreen startup and export checks passed; `scripts/verify_release.ps1`
also passed startup, restart persistence, database integrity, and six CSV/XLSX
export checks. The bundle scan found no database, TSV, MGD+, Dhruvil, staging,
or research data files. EXE SHA-256:
`E097AFC64898817795FEE3AD32973204581A6521173D08E286652023EF379DEC`.

The installer was not compiled: Inno Setup 6 is not installed in this
environment. Native GUI and DPI inspection remain outstanding. The persisted
13-stage import wizard is not implemented, large-file import is still not
chunked, the 500k analytics targets remain unmet, source permissions are
unverified, and production history remains empty. Client delivery is not
approved.
