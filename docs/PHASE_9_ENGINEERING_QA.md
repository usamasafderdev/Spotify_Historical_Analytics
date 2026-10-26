# Phase 9 engineering QA and release assessment

2026-10-26, Windows developer host, application 0.1.0. **Engineering release candidate; not approved for final client delivery.** The client still needs to decide between a complete bundled historical dataset and client-supplied imports. No research source has been commercially approved, and no complete 2017-2026 coverage is claimed.

## 1. Files changed and retained scope

Application changes in this phase:

- `src/spotify_historical_analytics/db.py`: memory scratch trees and artist aggregate query rewrite. These changes are already present in the current HEAD checkpoint; absence from a subsequent working diff does not mean they were untested.
- `src/spotify_historical_analytics/exports.py`: explicit synthetic export support, consistent read snapshot, atomic replacement, integer Excel formats, wrapping.
- `src/spotify_historical_analytics/import_sessions.py`: exact Decimal/integer validation and signed SQLite integer bounds.
- `src/spotify_historical_analytics/ui/import_dialog.py`: actionable corrupt-file, encoding, access, and disk-space errors with logged diagnostics.
- `src/spotify_historical_analytics/ui/main_window.py`: compact actions, responsive KPI/chart layout, readable axes, correct numeric bar-chart axis, chart label room, bounded scrollable details with fixed Close controls, synthetic titles/banners, export controls, metadata-button state, stale-read cancellation and safe shutdown, clearer invalid-date message, table tooltips.
- `src/spotify_historical_analytics/ui/workers.py`: cancellable dashboard reads, SQLite progress handler, synthetic export parameter.
- `src/spotify_historical_analytics/__main__.py`: opt-in QA entry point and clean demo smoke shutdown with a stoppable timeout.
- New `ui/phase9_qa.py` and `ui/windows_capture.py`: isolated Windows Qt acceptance automation and native HWND capture.

Build/QA files: `packaging/installer.iss`, `packaging/windows.spec` (generated notices and exclusion of the unused Virtual Keyboard plugin), `scripts/build_windows.ps1`, `scripts/build_installer.ps1`, `scripts/verify_release.ps1`; new `scripts/run_phase9_visual_qa.py`, `scripts/test_installer_isolated.ps1`, `scripts/write_release_notices.py`; new `tests/test_phase9_correctness.py`, `tests/test_phase9_edges.py`; updated `tests/test_ui_smoke.py`.

Documentation: `README.md`, `docs/CLIENT_REQUIREMENTS.md`, `CLIENT_HANDOVER_DRAFT.md`, `DEPENDENCY_LICENSES.md`, `GUI_AGENT_INSPECTION.md`, `METRIC_DEFINITIONS.md`, `PERFORMANCE_BEFORE_AFTER.md`, `RELEASE_QA_CHECKLIST.md`, `WINDOWS_INSTALLATION_GUIDE.md`; new this report, `USER_GUIDE.md`, and `docs/screenshots/phase9/` evidence. The earlier single-dialog import/theme/research separation work was retained; this phase did not recreate the application or reintroduce the wizard. No commits, client messages, purchases, or research-source imports were performed by this QA work.

The [working-tree file manifest](screenshots/phase9/working-tree-files.json) lists exact repository paths, including generated/pre-existing bytecode separately identifiable by suffix. It is a snapshot of the shared workspace, not a claim that every dirty file originated in Phase 9.

## 2. Implementation and verification matrix

"Working" means the listed synthetic/automated behavior was demonstrated, not client acceptance or full historical-data validation.

| Feature | Implemented | Tested | Working | Defect / limit |
|---|---|---|---|---|
| Overview and empty state | Yes | Independent totals, real Windows Qt, packaged screenshots | Yes | No approved historical records |
| Top Songs | Yes | Arithmetic, dates/search, numeric sorting, details, exports | Yes | Native mouse/keyboard acceptance still required |
| Top Artists | Yes | Collaborator full credit, deduplicated mappings, unresolved fallback | Yes | Totals overlap across collaborators by design |
| Top Albums | Yes | Exact mappings, distinct edition IDs, trends, details | Yes | Requires supplied stable mappings; no inferred albums |
| Daily/weekly and inclusive dates | Yes | Oracle boundaries, empty periods, GUI filter transitions | Yes | Physical calendar-popup interaction not separately inspected |
| Charts | Yes | Populated trend/bar widgets and inspected screenshots | Yes | Manual zoom/hover/accessibility acceptance remains |
| Coverage and sources | Yes | Inventory and all-page GUI checks | Yes | Observed coverage does not prove completeness |
| Simple import | Yes | CSV/XLSX/GZ, known/unknown schemas, native Qt dialog | Yes | No manifest or wizard; rights remain unverified |
| Import transactions | Yes | Conflict, duplicate, cancellation, changed-file, integrity tests | Yes | Large production-source timings remain to be profiled |
| Exports | Yes | Reopened CSV/XLSX against arithmetic; 12 GUI demo reports | Yes | Excel desktop visual review not performed |
| Settings and backup | Yes | Actual Save control, reopen integrity, persisted folder settings | Yes | Restore has no client UI |
| Isolated demo | Yes | All seven pages, details/exports, Return to Real | Yes | Generated fixture only, never production history |
| Background queries | Yes | Active SQLite interruption, generation guards, filter/close checks | Yes | Memory scratch allocation grows with query size |
| Errors and recovery | Yes | Corrupt files, ENOSPC simulation, migration failure, restart | Partial | Real full disk/Windows ACL failure not induced |
| EXE | Yes | Separate packaged startup, GUI, import/export/demo tests | Yes on host | Clean Windows VM absent |
| Setup | Yes | Host lifecycle under isolated product identity | Yes on host | Not clean-machine or separate-account acceptance |
| Signing/license release | Partial | Authenticode and inventory inspection | Pending | Unsigned; final per-component review open |
| Historical data delivery | Pending client | No source approval asserted | Pending | Bundling versus client imports undecided |

## 3. Broken behavior discovered

Demo ranking exports were disabled and excluded synthetic rows. Returning from demo could enable the obsolete metadata-only action. Fixed layouts crowded small windows and details could extend past the available desktop. Chart axis captions collided with ticks, bar values clipped, and screenshot inspection found stream counts formatted as calendar dates on the horizontal Top Songs axis. Float-based stream parsing could round exact large integers. Superseded dashboard reads kept consuming SQLite work; shutdown could block behind a modal wait prompt. Export failure could leave a partial destination. Installer discovery missed the per-user Inno installation, and version parsing contained invalid PowerShell quoting. Finally, the demo smoke path exited without closing its SQLite database, triggering a Windows temporary-directory cleanup exception despite a successful exit code.

## 4. Fixes and practical results

The defects above were corrected and exercised again. The bar chart now uses a numeric axis while temporal charts retain DateAxisItem. Detail dialogs have scrollable content and an always reachable Close row. The synthetic notice wraps at narrow widths rather than clipping. Read-only dashboard work is cancelled before shutdown; import/export writes retain their existing wait protections. Reports are written beside the target and replaced only after successful completion. Demo reports explicitly identify their origin. The smoke path closes databases before removing its temporary directory and cancels its timeout; the installer QA now checks newly appended ERROR/CRITICAL log entries as well as exit codes.

## 5. Actual visual inspection evidence

Development and packaged EXE were opened using Qt's **windows** platform, not only offscreen tests. Automation used real Qt navigation, search, sorting, date/chart controls, double-click detail actions, Save dialogs, backup, imports, and Return to Real. Final screenshots are in [the evidence folder](screenshots/phase9/), including [the contact sheet](screenshots/phase9/inspection-contact-sheet.jpg).

Representative full-size images: [Overview](screenshots/phase9/packaged/demo-01-desktop.png), [Songs](screenshots/phase9/packaged/demo-02.png), [Artists](screenshots/phase9/packaged/demo-03.png), [Albums](screenshots/phase9/packaged/demo-04.png), [Coverage](screenshots/phase9/packaged/demo-05.png), [Import page](screenshots/phase9/packaged/demo-06.png), [Settings](screenshots/phase9/packaged/demo-07.png), [album detail](screenshots/phase9/packaged/detail-albums-desktop.png), [import preview](screenshots/phase9/import/04-preview-and-coverage.png), [mapping](screenshots/phase9/import/08-optional-mapping.png), [import error](screenshots/phase9/import/10-import-error.png), and [date error](screenshots/phase9/packaged/invalid-date-error.png).

Images ending `-desktop` use Windows PrintWindow on the application's actual HWND, including the system titlebar; the others use QWidget capture. A transient warning or hidden startup's native capture can be black, so the final native capture run explicitly showed the application and the inspected QWidget image is the error-dialog evidence. An initial generic desktop capture recorded another foreground window and was excluded from published evidence. No claim of native visual correctness is based on a discarded or blank capture.

The nine-combination matrix covers 1366x768, 1600x900, 1920x1080 at target 1.0/1.25/1.5 Qt device pixel ratios. The runner computes logical space after titlebar/taskbar allowance and changes QT_SCALE_FACTOR; it **does not change the physical Windows display configuration**. This is Windows Qt scaling/window-constraint automation, not physical DPI verification. Manual Windows focus, keyboard accessibility, native shell file dialogs, multi-monitor behavior, and actual display-setting changes remain unverified. Qt widget file dialogs were exercised. Narrow charts stack and all content remains scrollable.

These constraints apply to the main window. `QScreen.availableGeometry()` still
reports the host monitor for detail-dialog bounds; the runner does not emulate
a smaller physical monitor's geometry. Dialog scrolling and Close controls were
inspected on the host, while physical smaller-monitor acceptance remains open.

## 6. Performance

Fresh baseline and after-query runs reused exactly the retained synthetic databases. No indexes were added, and database sizes remained 18.68/75.49/370.28 MiB. Single observed runs, with uncontrolled cache warmth/host load:

| Rows | Summary before / after ms | Songs before / after ms | Artists before / after ms |
|---:|---:|---:|---:|
| 25,000 | 30.01 / 34.07 | 57.34 / 70.79 | 36.10 / 41.27 |
| 100,000 | 619.15 / 144.83 | 689.66 / 257.56 | 353.92 / 181.79 |
| 500,000 | 7,887.67 / 881.79 | 2,809.91 / 1,277.12 | 5,828.37 / 853.40 |

The artist query now deduplicates supplied relationships once and uses a single chart scan; scratch trees use memory. Existing covering indexes are used. DISTINCT/grouping trees still exist. Memory use trades off against disk latency. Small-data runs did not improve. Baseline insertion was 2.538/24.550/168.399 seconds; the first full-suite after run was 6.070/29.794/179.027 seconds. Insertion improvement is **not** established. A UI-loaded 500k run measured summary 1,537 ms, songs 2,427 ms, artists 1,468 ms and peak RSS 344 MiB, so all latency targets are not met consistently. See [full methodology](PERFORMANCE_BEFORE_AFTER.md) and [plans](screenshots/phase9/query-plans-and-after.json). The later final regression run executes performance tests as well; it is not an additional controlled A/B benchmark.

## 7. Import status

One **Import Historical Music Data** dialog supports CSV, CSV.GZ and XLSX with automatic recognized-schema mapping and optional same-dialog mapping. Background chunked staging reports progress, source/date/USA counts, duplicates and validation warnings. No mandatory JSON rights manifest, licensing questionnaire, or multi-page wizard remains in the client flow. The separate research pipeline's approval safeguards remain intact.

Packaged GUI fixture: 4 processed rows, 2 valid USA rows, 2 rejected, 1 imported, 1 duplicate skipped; integrity `ok`. Changed source bytes block final import. Cancellation closes safely. Unit/service checks cover explicit weekly periods, wrong market, invalid dates/streams, metadata conflicts, transaction rollback and repeat import. MGD+/Dhruvil recognition uses schemas, not automatic import of the research files. Exact integer parsing preserves 9,007,199,254,740,993; nonintegral/nonfinite/out-of-range and malformed comma values reject. User-supplied source notes remain unverified, not commercial authorization.

## 8. Independent analytics accuracy

`tests/test_phase9_correctness.py` constructs expected dictionaries by Python arithmetic over deterministic tuples, independently of SQL. Daily US real rows sum to **420**: Song Alpha 220, Beta 80, Gamma 120. Alice receives 300, Bob 220, and unresolved credit 120. Edition 1 receives 300 and Edition 2 receives 220 even with the same album display name. A weekly 900 row, Canadian 9,999 row, and synthetic 30 row are separately filtered. Repeated record insertion and duplicate attribution rules must not double count.

Tests cover daily/weekly selection, inclusive first/last date, one-day/empty intervals, real/demo inclusion, song/artist search, trend per-date totals, rankings and both export formats. The complete suite also covers supplied artist/album metadata, exact mapping coverage, and rollback. Metrics are documented in [METRIC_DEFINITIONS.md](METRIC_DEFINITIONS.md); artist/album totals can overlap by attribution/edition and must not be added as unique platform totals. The Overview artist KPI counts whole credited strings, distinct from the ranking's supplied artist IDs.

## 9. Export verification

Independent tests reopen CSV and XLSX for each ranking and compare stream columns to the Python oracle, including explicit demo inclusion. Existing export tests cover Unicode, empty results, filters, source/metric definitions, and formula-injection escaping. The Windows GUI runner produces and reopens **12** reports: three rankings, two cadences, two formats, with a 2020 date filter and clearly labeled synthetic data. Packaged release smoke additionally parses six real-mode synthetic-fixture reports. Excel counts use numeric cells with `#,##0`; files use frozen headers/filtering and separate definitions/coverage sheets. An injected ENOSPC preserves the existing destination. Excel desktop itself was not opened.

## 10. Automated checks

Final `python -m pytest -q`: **155 passed in 272.42 seconds**, including the three 25k/100k/500k performance cases. `python -m compileall -q src scripts tests` and `git diff --check` passed. Final application source includes the narrow-banner wrapping fix and demo-shutdown regression. Packaged release smoke, separately launched Windows GUI/import checks, all nine simulated scaling scenarios, and isolated installer lifecycle checks passed after rebuilding. See [machine-readable final results](screenshots/phase9/final-checks.json), [test output](screenshots/phase9/final-tests.log), [installer results](screenshots/phase9/installer-results.json), and [bundle inventory](screenshots/phase9/bundle-audit.json).

| Final unsigned artifact | SHA-256 |
|---|---|
| `USMusicChartsAnalytics.exe` | `6710EB8DF605308F1F244D9A4D8B60EC1730BD35132258B47C6CC8C2EC5ECF32` |
| `US-Music-Charts-Analytics-Setup.exe` | `0D36E4A234D5425EF086EF8E2AE65EA5B184C3AF65205E4D63010473303C8D8D` |

Both artifacts report `NotSigned` from Windows Authenticode inspection. The full onedir SHA256SUMS manifest was rechecked. The final bundle contains 45 notice files and 69 byte-verified upstream PyQtGraph color-map CSVs; no historical CSV/XLSX/SQLite/Parquet data files were found. The old wizard and unused Virtual Keyboard module/plugin are absent. Default AppData routing is covered by unit tests; the native GUI/lifecycle checks use explicit isolated directories.

## 11. Packaged EXE

`dist/USMusicChartsAnalytics/USMusicChartsAnalytics.exe` is the PyInstaller onedir Windows x64 application. Keep the entire folder. It was rebuilt after application changes, with bundled assets, Qt platform plugins, chart libraries and generated notices. Tests use isolated data-directory overrides, leaving the normal production database untouched. Default path tests verify `%LOCALAPPDATA%\USMusicChartsAnalytics\database\analytics.db`; installed executable launch is also checked with Python removed from PATH. This supports standalone packaging on this host, not a clean-OS proof. No research file paths or historical databases are required at runtime.

## 12. Setup installer

Inno Setup **6.7.3** was already installed at `%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe`. Discovery now checks PATH, both Program Files roots, and per-user Programs for versions 7/6; no privileged software was installed. Production output is `dist/installer/US-Music-Charts-Analytics-Setup.exe` with a sibling SHA-256 file.

`test_installer_isolated.ps1` compiles the same payload under a distinct QA GUID/name, installs under `build/phase9/installer-qa/installed`, verifies Start Menu/Desktop shortcut targets and the installed EXE hash, starts without Python on PATH, inserts a persistence marker, upgrades package version 0.1.0 to 0.1.0.1, rechecks marker/integrity/export/demo, then uninstalls. The version bump tests installer upgrade mechanics with the same application payload; it is not a cross-version application schema migration. App files/shortcuts are removed and separate QA user data is retained. Real installation identity/data are untouched. This is same-account host isolation, not a disposable VM or separate Windows account.

## 13. Native Windows QA status

Completed: real Windows-platform Qt windows, actual HWND captures for primary windows/details, image inspection, widget-driven all-page and import/export scenarios, packaged and source execution. Partial: native desktop interaction and true DPI acceptance. No configured clean Windows VM was available. No security prompt was approved or protection bypassed. The earlier statement that only offscreen evidence existed is superseded by these qualified Windows captures.

## 14. Outstanding technical limitations

- Clean Windows 10/11 x64 installation/startup/import/export/upgrade/uninstall remains mandatory before client handover. Removing Python from PATH on this host does not establish absence of developer-installed runtimes.
- Physical 100/125/150% display settings, multiple monitors, keyboard/focus/accessibility, native file chooser behavior, manual tooltip/zoom interactions, and Microsoft Excel rendering remain acceptance work.
- 500k insertion still takes minutes and indexes consume substantial disk. Client-like larger sources and high-cardinality memory use need profiling; scratch-memory allocation is not bounded by the chunk size.
- Read-only/disk-full handling was checked with injected PermissionError/ENOSPC failures, preserving an existing report and removing temporary files. The user's disk was not filled and Windows ACLs were not changed. Concurrent launches use a tested single-instance lock; a two-EXE native prompt scenario was not manually driven.
- Metadata-only import is intentionally disabled, restore has no dedicated UI, and accurate album analysis requires supplied mappings.
- Executable and installer are unsigned. Final Qt module-by-module licensing, corresponding-source/replacement materials and full transitive notices review remain open. The generated core notices are not a compliance certificate. Inno requests commercial purchase but its FAQ says it is not strictly required; no purchases or key changes were made. See [dependency review and official sources](DEPENDENCY_LICENSES.md).

## 15. Data and permissions awaiting clarification

The client must decide whether complete preloaded historical data is part of delivery or whether they will supply datasets for import. That choice was not made here. Research candidates remain separate: Dhruvil 2017-2021, MGD+ through 2022-03-13, and sampled Zenodo weekly archives for 2022-2026. None is asserted commercially cleared. Sampled weekly observations cannot fill missing daily history. Source provenance, actual years/USA semantics, permitted processing/commercial use/exports, and stable album/artist mappings need source-specific review after the client's decision. Removing a manifest UI grants no permission. No client contact, subscription purchase, scraping, or unauthorized bundling occurred.

## 16. Release readiness

**Ready for controlled engineering/demo review; not ready for final paid-client release.** The current improvements are usable under either data-delivery decision. Final delivery requires the client's data scope/acceptance, approved sources and verified coverage, a successful clean-machine lifecycle run, physical desktop acceptance, and final signing/security-policy and dependency-license resolution. Synthetic demonstrations and passing tests are evidence of application behavior, not evidence of complete historical data or permission to commercialize it.
