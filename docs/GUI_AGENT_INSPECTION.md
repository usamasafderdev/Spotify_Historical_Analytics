# GUI Agent Inspection

## Inspection capability

No native Windows desktop control/screenshot integration was available in the session. Browser automation tools are not appropriate for native PySide6 windows. Offscreen Qt widget tests and an offscreen screenshot can validate widget state/rendering but cannot prove normal desktop visuals, Windows scaling, focus behavior, OS file dialogs, or actual user-perceived responsiveness.

## Feature implementation and verification matrix

| Feature | Source | Implementation status | Functional verification | Defects / remaining action |
|---|---|---|---|---|
| Overview | `ui/main_window.py`, `ui/workers.py`, `db.py` | Implemented with KPI/cards, charts, empty state | Offscreen UI empty-state and populated synthetic demo tests; DB summary tests | Interactive Windows visual review outstanding |
| Top Songs | `ui/main_window.py`, `db.py` | Search, sorting, date/chart filters, details | Offscreen search/date tests, table sorting, DB detail tests | Native interaction and large-data responsiveness review |
| Top Artists | `ui/main_window.py`, `db.py` | Exact-ID full-credit and whole credited-string fallback | Metadata/attribution tests, populated demo ranking and detail-dialog test | Performance target remains unmet at 500k rows |
| Top Albums | `ui/main_window.py`, `db.py`, `metadata_importer.py` | Stable-ID mapped editions only; honest empty state | Mapping tests, synthetic demo ranking/details, no-false-mapping coverage | Real album metadata is absent; editions need authorized mappings |
| Data Sources & Coverage | `ui/main_window.py`, `db.py` | Production inventory, 2017–2026 display, status labels | Inventory tests and offscreen coverage page assertions | Does not display external research staging by design |
| Settings | `ui/main_window.py`, `db.py` | Local data location and backup button | DB backup/restore API tests; widget page created in offscreen smoke | GUI file dialog and real backup/restore action not automated |
| Date filters | `ui/main_window.py`, `db.py` | Inclusive date bounds and presets | Widget filter test and invalid range validation test | Native calendar popup review outstanding |
| Search / sorting | `ui/main_window.py`, `db.py` | Search debounce and table sorting | Offscreen search and sort regression | Native keyboard/accessibility review outstanding |
| Interactive charts | `ui/main_window.py` | PyQtGraph time-series and ranking chart | Offscreen populated chart item assertions | Axes, hover, resize, and native visual review outstanding |
| Song/artist/album details | `ui/main_window.py`, `ui/workers.py` | Background detail workers and dialogs | Synthetic demo detail dialogs opened/closed with real DB detail results | Native modal behavior and error dialog review outstanding |
| CSV/XLSX imports | `importer.py`, `ui/workers.py`, `ui/main_window.py` | Background, transaction-wrapped imports | Import API and worker tests; rollback tests | No guided 13-stage persisted GUI wizard; CSV/XLSX currently loaded in memory |
| Metadata imports | `metadata_importer.py`, `ui/main_window.py` | Preview, column mapping, stable IDs, transaction | Metadata parser/rollback tests | File-picker/dialog interaction not automated |
| CSV/XLSX exports | `exports.py`, `ui/workers.py` | Filtered CSV/XLSX with definitions and coverage | Export equivalence and formula-escaping tests; packaged export smoke test in prior build | Rebuild/reverify current Phase 8 source |
| Synthetic demo | `db.py`, `ui/main_window.py`, `__main__.py` | Separate temporary DB and clear global banner | Widget-level mode switch, rankings, date/chart filter, return-to-real tests | Interactive native review outstanding |
| Database persistence | `db.py`, `runtime.py` | SQLite AppData path, schema initialization | Reopen and backup/restore tests | Current Phase 8 EXE package verification required |
| Backup / restore | `db.py`, `ui/main_window.py` | SQLite online backup and verified restore API; GUI backup action | Database API tests | GUI restore picker does not exist; verify whether product needs restore UI |
| Error handling | `ui/workers.py`, `runtime.py`, import modules | Background failures logged/notified; transaction rollback | Worker failure and database rollback tests | Full end-user error walkthrough outstanding |
| Installer readiness | `packaging/installer.iss`, `scripts/build_installer.ps1` | Installer script exists | Prior inspection found Inno Setup absent | Installer compilation/installation test blocked by missing Inno Setup |

## Verified behavior this iteration

- `python -m pytest -q`: 92 passed after the Phase 8 changes.
- Focused `tests/test_ui_smoke.py`: 6 passed after the table-layout updates.
- Normal GUI visual behavior is **not** claimed from offscreen tests.
- The Phase 8 EXE was rebuilt; packaged startup, restart persistence, database integrity, and six CSV/XLSX export smoke checks passed.
- Inno Setup is unavailable, so installer compilation and installation were not verified.

## Offscreen screenshot findings and follow-up

The 1366×768 offscreen screenshots showed unsupported sidebar icon glyphs
rendering as empty boxes, duplicate row numbers beside explicit rank columns,
and clipped content in the 13-column coverage table. The sidebar now uses
plain-text initials, ranking and coverage tables hide the redundant vertical
row header, and coverage columns size to their contents so narrower windows
can scroll horizontally. The table corner also has an explicit dark-theme
style. Widget assertions cover these settings.

These adjustments address the specific offscreen findings; they do not replace
native Windows review. Native inspection at 1366×768, 1600×900, 1920×1080 and
100%, 125%, and 150% DPI remains outstanding.
