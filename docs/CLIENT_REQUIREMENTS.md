# Client Requirements Summary

## Core request
Build a professional Windows desktop analytics application for a client analyzing historical US Spotify chart data. The application must use lawfully imported datasets, avoid false claims, and support filtering, KPIs, rankings, artist/album analysis, provenance, and exports.

## Primary constraints
- Windows 10 / 11, 64-bit
- Python 3.12+ and PySide6 desktop UI
- SQLite for local storage
- Data imported from user-supplied CSV/XLSX files
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
