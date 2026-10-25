# Phase 5: Windows Release Preparation

## Implemented release infrastructure

- Independent product display identity: **US Music Charts Analytics**. The internal Python import package remains `spotify_historical_analytics` for continuity.
- Central application version is `src/spotify_historical_analytics/__init__.py::__version__`. The build script generates matching Windows executable version metadata.
- Original non-Spotify icon source is `assets/app_icon.svg`; `scripts/generate_icon.py` produces the Windows `.ico` used by the executable, taskbar, and installer.
- `packaging/windows.spec` defines a 64-bit PyInstaller **onedir, windowed** build and includes the Qt, PyQtGraph, Pandas, and OpenPyXL runtime assets using PyInstaller hooks.
- `packaging/installer.iss` defines a per-user Inno Setup installer with Start Menu entry, optional desktop shortcut, upgrade identity, uninstall registration, and no removal of the external per-user database.
- Build, installer, and packaged launch verification commands are in `scripts/build_windows.ps1`, `scripts/build_installer.ps1`, and `scripts/verify_release.ps1`.
- Windows user state is rooted at `%LOCALAPPDATA%\USMusicChartsAnalytics\`, or at the explicit `SPOTIFY_ANALYTICS_DATA_DIR` override. Database, logs, backups, exports, and settings use separate subfolders.
- A detected prior development database is offered for explicit, copy-only migration. Migration is integrity-checked, never replaces an existing new database, and retains the old source.
- A per-user `QLockFile` prevents a second application instance from opening the same database for concurrent writes.
- Settings persist the last-used import and export folders through an atomic JSON write. Logs rotate locally and background workers log stack traces privately instead of showing tracebacks.
- Database backup now rejects an existing destination; restore copies and integrity-checks to a temporary file before replacement and keeps the current database if verification fails.
- First launch presents the actual empty dashboard with import and data-coverage navigation available. Synthetic preview remains opt-in and isolated.
- `--release-export-test` generates an isolated temporary fixture at runtime and verifies songs, artists, and albums in both CSV and XLSX formats. No fixture dataset, database, or export file is stored in the EXE bundle.

## Reproducible Windows commands

From the project root in PowerShell:

```powershell
python -m pip install -e ".[test,build]"
.\scripts\build_windows.ps1
.\scripts\verify_release.ps1
```

The expected executable is `dist\USMusicChartsAnalytics\USMusicChartsAnalytics.exe`. The build script runs pytest, compileall, icon generation, the PyInstaller onedir build, an offscreen first-launch smoke test with an isolated data root, and the six-format packaged export check. A recursive SHA-256 manifest is generated for the complete onedir bundle.

Install Inno Setup 6 from its official site and run:

```powershell
.\scripts\build_installer.ps1
```

The expected installer is `dist\installer\US-Music-Charts-Analytics-Setup.exe`. The current development environment has PyInstaller available; Inno Setup was not detected when Phase 5 began. Installer compilation and installation QA are therefore pending unless the script is run successfully later.

## Verification status

The pre-Phase-5 suite had **36 passing tests**. The expanded suite has **46 tests**, including Phase 5 coverage for user directories, data-root selection, settings persistence, safe legacy database copy and failure, icon/resource paths, app identity, single-instance locking, database restart persistence, and safe backup/restore. The final build run passed **46/46 tests in 10.83 seconds**.

The final Windows 11 development-host build used Python 3.14.3 and PyInstaller 6.22.0. The onedir EXE is version **0.1.0**, has a size of **19,527,681 bytes**, and its SHA-256 is `5EA0F66E060F440E99FE46F8E97A9D9E76E68BE00C006A0A182C0193FAB0D69F`. The bundle's `SHA256SUMS.txt` contains 1,705 payload-file hashes. The packaged executable launched in Qt offscreen mode, created a fresh database under an isolated data-root override, and exited successfully. The release verifier restarted the packaged app and confirmed a database marker persisted; SQLite integrity reported `ok`. The frozen export self-test returned exit code 0 for all six formats. A bundle scan found no test/example/fixture directories, `.xlsx`/`.db` archives, or historical chart files; included `.csv` files are PyQtGraph color-map rendering resources, not chart observations.

The executable passed the packaged startup, isolated database creation, restart-persistence, SQLite-integrity, and six CSV/XLSX export checks. Inno Setup is still unavailable on the build host, so no installer was compiled. An offscreen launch is a startup smoke test, not normal Windows visual QA. It does not prove clean-machine behavior, 100%/125%/150% display scaling, file-dialog behavior, installer/uninstaller behavior, or data persistence after a true upgrade. Follow [RELEASE_QA_CHECKLIST.md](./RELEASE_QA_CHECKLIST.md) and [WINDOWS_VISUAL_QA_CHECKLIST.md](./WINDOWS_VISUAL_QA_CHECKLIST.md).

## Explicitly incomplete

- No real historical dataset was bundled or requested. The client's 2017–2026 data, provenance, rights, intended derived analysis, and redistribution permission remain unverified; see [DATA_ACQUISITION_STATUS.md](./DATA_ACQUISITION_STATUS.md).
- The installer has not been compiled, installed, upgraded, or uninstalled in a clean Windows VM.
- No trusted code-signing certificate was available or used. The installer and EXE are unsigned and may trigger SmartScreen warnings.
- Dependency licensing, Qt LGPL obligations, notices, and any required relinking/source-offer mechanics require release/legal review; see [DEPENDENCY_LICENSES.md](./DEPENDENCY_LICENSES.md).
- Packaged smoke testing exercises all six export formats with a generated temporary test database. Native Windows save-dialog interaction and export-filter selection still require installed UI QA.
- Client handover and final delivery are not approved by these engineering checks.
