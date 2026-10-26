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

Phase 8B implements the persisted, 13-stage CSV/XLSX wizard, separate chunked
staging database, resumable checkpoints, rights-manifest/evidence hash checks,
transactional production import, identity mapping, integrity check, and
first-run recovery prompt. Focused synthetic workflow tests are documented in
[IMPORT_WIZARD_QA.md](./IMPORT_WIZARD_QA.md) and
[PHASE_8B_IMPORT_WORKFLOW.md](./PHASE_8B_IMPORT_WORKFLOW.md).

The current generic mapping wizard is not automatically wired to source-specific
MGD+ or Dhruvil adapters. The separate metadata-only import control is disabled
until it is rights-gated. No MGD+ or Dhruvil research data was imported.

## Release status

The current Phase 8B Windows x64 EXE was rebuilt from this source after the
full test suite passed. Build smoke tests, `scripts/verify_release.ps1`
(startup, restart persistence, SQLite integrity, six CSV/XLSX export checks),
and the packaged synthetic-dashboard smoke test passed. A bundle scan found no
SQLite database, TSV, MGD+/Dhruvil source, research staging, or import-session
database. EXE SHA-256:
`F5027F776D94CA7E389E04619A37B10F017C01171282143DD6FBF0121FB6F185`.

The automated suite finished with **106 passed**. `python -m compileall -q
src scripts tests` and `git diff --check` passed. Synthetic benchmark results
are in [PERFORMANCE_BEFORE_AFTER.md](./PERFORMANCE_BEFORE_AFTER.md); the
500k summary and artist latency goals remain unmet.

The developer production database observed during this work is
`%LOCALAPPDATA%\USMusicChartsAnalytics\database\analytics.db`: it had 0 chart
rows, 0 synthetic rows, and schema version 1 when checked read-only. It was
not modified by tests or packaged smoke tests; the next normal application
startup will apply the additive schema version 2 initialization. Research
staging remains isolated and no candidate rows were imported.

The installer was not compiled because Inno Setup 6 is unavailable. Native
interactive Windows visual inspection and 100%/125%/150% DPI checks remain
outstanding. MGD+/Dhruvil permissions remain unverified and client delivery is
not approved.
