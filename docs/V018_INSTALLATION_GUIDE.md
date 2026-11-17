# US Music Charts Analytics 0.1.8: installation

INTERNAL-READY evaluation only. External redistribution of the supplied historical data has not been authorized. The build is unsigned; use your organization's approval process without disabling Windows security.

1. Extract the handover ZIP to a local folder and verify Setup against `SHA256SUMS.txt`.
2. Use Windows 10/11 x64. Install the official Microsoft Visual C++ v14 x64 runtime 14.44.35211.0 or newer if Setup requests it: https://aka.ms/vc14/vc_redist.x64.exe. Setup neither bundles nor downloads Microsoft runtime DLLs.
3. Run Setup as your normal Windows user. Choose a drive with space for the application and bundled seed. Launch **US Music Charts Analytics** from Start. No Python, Git, VS Code, Spotify account, or manual database setup is required.
4. On first launch the bundled historical seed is copied once into the writable per-user database. Allow space for both the installed seed and the user database, plus future imports and backups. First initialization can take time while integrity is checked.

The default data folder is `%LOCALAPPDATA%\USMusicChartsAnalytics`; Settings opens its data/log locations. For managed installations with limited C: storage, an administrator/operator may set the per-process or per-user `SPOTIFY_ANALYTICS_DATA_DIR` to a writable folder on another drive before launch. Do not move an active database. This override is optional, not a requirement for normal users.

Updates and reinstalls never replace an existing user database with the seed. Your weekly imports remain in that database. Uninstall removes application files, not the separate user data. Use **Settings > Create database backup** before updates; **Restore database** validates a selected backup and preserves the previous database first.

The installed application does not depend on the developer's Downloads folder or integration directory. Analysis and exports work offline. Artwork is represented by retained URL references, not a bulk image cache.

Third-party notices, Qt source/replacement materials, runtime terms, and the source manifest are installed inside `_internal\compliance`, `_internal\notices`, and the documentation folder. Keep these materials with the application. The original dependency-r3 materials are retained; the current runtime normalization inventory identifies any staged binary import-name normalization.
