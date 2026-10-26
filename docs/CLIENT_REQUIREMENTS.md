# Client Requirements Summary

Current verification and release status: [Phase 9 engineering QA](PHASE_9_ENGINEERING_QA.md), with actual packaged Windows screenshots, independent arithmetic checks, benchmark evidence, and isolated installer lifecycle results. Earlier phase notes below are historical. The client has not yet decided whether the product must bundle complete historical data or accept client-supplied datasets. No complete 2017-2026 data or commercial source approval is claimed.

## Core request
Build a professional Windows desktop analytics application for a client analyzing historical US Spotify chart data. The application must use lawfully imported datasets, avoid false claims, and support filtering, KPIs, rankings, artist/album analysis, provenance, and exports.

## Primary constraints
- Windows 10 / 11, 64-bit
- Python 3.12+ and PySide6 desktop UI
- SQLite for local storage
- Data imported from user-supplied CSV/XLSX and supported CSV.GZ files
- No scraping, unauthorized API usage, or unsupported dataset bundling
- No real Spotify branding, credentials, or login flow
- Data must be clearly marked, provenance-aware, and quality-flagged

## Required product behavior
- Dashboard with KPI cards and coverage analytics
- Date filtering with inclusive ranges and daily/weekly separation
- Song rankings with search, sorting, pagination, and drilldown
- Artist and album analytics using charting-song and charting-track sums
- Data-quality banner and empty states when no valid data exists
- Import validation, duplicate detection, and rollback-safe processing
- CSV/XLSX export for filtered result sets
- Settings, backup/restore, and source attribution

## Delivery expectations
The project must provide an initial working Windows app foundation with a documented data model, validation rules, and a real command-line/testable implementation. The app should not misrepresent historical data as complete when the underlying source is partial or unavailable.

## Phase 2 implementation status
- Implemented: native dashboard navigation, shared date/chart filters, real-data KPIs and charts, searchable/sortable song rankings, song details, credited-artist aggregates, source inventory, observed coverage reporting, import feedback, and backup.
- Updated in Phase 3: functional artist rankings and details using stable IDs or whole credited-string fallback; album rankings only for user-supplied stable-ID mappings; metadata preview/mapping import; transactional background imports; and background dashboard aggregate queries.
- Limitations: coverage is observational and unverified; source completeness and licensing are not inferred; normal Windows desktop visual review is still required.
- Verification: `python -m pytest -q` includes attribution, mapping, migrations, rollback, worker, performance, and offscreen UI regressions.

## Phase 7 implementation status

- Implemented: read-only chunked MGD+ and Dhruvil schema adapters with source-file digest and row provenance; stable URL ID extraction; streamless Viral 50 separation; exact multi-artist metadata mapping; expanded production coverage inventory and 2017–2026 year display; explicit research/production boundary; and stronger evidence/scope checks for research-staging production imports.
- Current import interface: one dialog with automatic MGD+/Dhruvil schema detection, same-dialog optional mapping, coverage/USA preview, background validation, transactional import, safe cancellation, backups, and integrity checks. The earlier 13-stage wizard and mandatory JSON manifest were removed at the user's request. The separate research pipeline's approval safeguards remain unchanged. Metadata-only import stays disabled; explicit associations can be imported with chart rows.
- Data status: no authorized historical real data confirmed in production; research sources remain unverified; album mappings and 2022–2026 authorized coverage are unavailable.
- Release status: build, packaged execution, automated GUI evidence, and remaining native desktop/DPI limitations are recorded in [SIMPLE_IMPORT_INTERFACE.md](SIMPLE_IMPORT_INTERFACE.md). Signing and installer readiness are not inferred from an EXE build.
