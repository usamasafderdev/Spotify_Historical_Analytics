# Windows Installation and Data Guide

Phase 9 produced `dist\installer\US-Music-Charts-Analytics-Setup.exe` using the
already-installed Inno Setup 6.7.3. A separate QA product identity and workspace
installation path were used for host install, shortcut, no-Python-on-PATH launch,
version upgrade, persistence, export, demo, and uninstall checks. This was not a
clean Windows VM or separate-account test. See [current evidence and hashes](PHASE_9_ENGINEERING_QA.md)
and the [version 0.1.0 user guide](USER_GUIDE.md). The artifacts remain unsigned
and final client delivery is not approved.

## Client installation

The release candidate is a per-user x64 application. If an installer has been compiled and approved, run `US-Music-Charts-Analytics-Setup.exe` from its verified release location. Windows may show an unsigned-publisher/SmartScreen warning because this build is not code-signed; do not bypass security controls unless the organization's normal software approval process explicitly authorizes the file.

The installer targets the current user's Programs folder, creates a Start Menu shortcut, and offers an optional Desktop shortcut. It should not need administrator elevation. The uninstall entry is registered with Windows. Uninstall removes the application files but intentionally leaves data under Local AppData.

## Data locations

`%LOCALAPPDATA%\USMusicChartsAnalytics\`

```text
database\analytics.db
logs\application.log
backups\
exports\
config\settings.json
```

Use **Settings → Open data folder** or **Open logs folder** in the app to navigate there. Import and export dialogs remember their most recent folders. These locations are per Windows user and are not placed in the installed application directory.

## Existing development database

At first start, the app checks known old development locations. If an existing database is found and no new database exists, the app asks whether to copy it. Choosing **No** leaves both the existing source and the new data store untouched. Choosing **Yes** makes an integrity-checked SQLite backup-copy into the new database folder. The legacy file is not moved or deleted. If copying fails, inspect the log and continue using the original development build until the issue is resolved. Never manually overwrite `database\analytics.db`.

## Backup and restore

Use **Settings → Create database backup**, select a new destination, and retain a second copy outside the computer. Existing backup paths are not overwritten. Before an upgrade, close the app and verify a recent backup exists.

The current application provides safe backup creation. Restoring remains an operator/developer workflow rather than a dedicated client UI: close all app instances, preserve a copy of the active database, then use a verified SQLite backup according to the approved support procedure. Do not replace a database while the app is running.

## Updates and uninstall

Install an approved newer build for the same per-user Windows account. The installer uses a stable product identity and should reuse the prior install directory. Application data is outside that directory and is not removed by upgrade or uninstall. Back up before upgrading and verify the source/rights records after restart. Reinstallation should reuse the existing user data folder.

## Offline and source requirements

The app does not require internet access, Spotify login, or cloud registration for startup and local analysis. Historical data is not included. Import only data for which the client has documented acquisition, processing, derived-metric, and export rights. User possession or source attribution is not proof of those rights.
