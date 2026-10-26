# Client Handover Draft — Not Yet Approved

## Product

US Music Charts Analytics is an independent Windows desktop app that analyzes locally imported chart rows. It is not affiliated with or endorsed by Spotify. The installed application is intended to run offline and does not require Python, a developer account, Spotify login, or cloud registration.

## Current delivery status

**Release candidate only. Not approved for final client delivery.** The final source build passed 46 automated tests, and the developer-host packaged executable passed isolated startup/database, restart-persistence, SQLite integrity, and all six CSV/XLSX export checks. The current executable is version 0.1.0 with SHA-256 `3AAA8595FC88FB572E567D3489C7321A01D538D3FA54730D47FC4852687DE141`. Installer compilation and clean-machine installation/upgrade/uninstall checks remain pending; Inno Setup was unavailable on the build host. The current build is unsigned unless an authorized signed artifact is produced separately.

## Historical data and rights

No authorized USA historical source covering 2017–2026 has been confirmed for this handover. No real historical dataset is bundled. The imported records are user-provided and must have documented rights for acquisition, retention, processing, derived metrics, exports, and commercial distribution. A user-provided file or in-app attribution note does not establish permission. Spotify policy applicability needs current counsel/platform review. See [DATA_ACQUISITION_STATUS.md](./DATA_ACQUISITION_STATUS.md).

## Local records and backups

Windows user data is stored under `%LOCALAPPDATA%\USMusicChartsAnalytics\`. It is intentionally separate from the installed files and is retained when the app is uninstalled. Back up the database before application updates and retain an off-device copy. A detected older database is copied only after an explicit prompt; the old file is retained.

## Import and export

Import only authorized CSV/XLSX chart observations and supplied artist/album metadata. Exports represent imported chart observations under the app's documented metrics and filters; they are not official or comprehensive Spotify totals. Confirm the source terms allow export and downstream sharing.

## Required sign-off before delivery

1. Validate exact historical data source, period, USA market, daily/weekly definitions, corrections, completeness, and metadata.
2. Obtain written acquisition, analytics, commercial-use, export, and redistribution permissions; complete legal/platform review.
3. Complete Qt and bundled-dependency license review and ship required notices/compliance materials.
4. Produce a signed or explicitly accepted unsigned installer and verify hashes.
5. Complete Windows VM installation, restart, import/export, update, persistence, and uninstall-preserves-data QA.
6. Obtain client visual and functional acceptance at supported display scaling and resolutions.
