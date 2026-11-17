# 0.1.8 INTERNAL-READY release verification

Verified on the existing Windows x64 development host on 2026-11-17. This is an unsigned internal evaluation release, not an externally authorized client delivery or clean-Windows-VM certification. No push or merge was performed.

## Data and integrity

- Native daily songs: one streaming pass over `charts_songs_daily.csv`, accepting 721,171 US observations; 26 invalid US rows were rejected and 44,540,833 non-US rows excluded.
- Legacy `charts.csv`: one streaming pass, 210,976 exact overlaps skipped and 153,208 differences quarantined. This includes 701 alternate-ID rows occupying already-established chart slots, corrected only in this task's incoming batch. No additional legacy rows enter totals. Detailed values remain in two SQLite conflict ledgers; IDs are not guessed to be aliases.
- `charts_artists_daily.csv` was already complete; its 368,000 US positions were preserved through manifest-based skipping. Metadata, 61,588 album positions and 3,262,204 listener snapshots remain separate and unchanged.
- Final songs: 721,171 daily observations on 3,606 dates, 2017-01-01 through 2026-11-15; 12,599 source-weekly observations on 63 sampled dates; 131,729 derived track/week observations on 516 Sundays. Daily and derived totals both equal 316,705,690,324; source-weekly total remains 42,913,401,825.
- Final read-only integration verification: `quick_check=ok`, zero duplicate song identities, zero daily dates above 200 accepted observations, and unchanged existing weekly/album/listener counts. Missing entries and partial weeks were not filled. The final seed was integrity-checked again during installed first-run initialization.
- Entities: 220,884 tracks, 75,200 artists, 26,631 albums; 349,341 track-to-artist and 28,984 album-to-artist links; zero track-to-album links; 705,473 URL references. Earlier integration's two invalid rows remain documented separately.

Exact source paths, sizes, modification times, SHA-256 values and schema fingerprints are in `local-data/v018-integration/source-manifest.json` and SQLite. Missing older schema fingerprints were backfilled from headers only, without rescanning large source bodies. Verification evidence is in `local-data/v018-work/integration-verification.json`.

## Focused tests and installed checks

**18 unique focused tests passed** in the final selected run. These cover daily imports and cross-source identity/slot conflicts, separate artist positions, source/daily/derived separation, full-history repeat counts and Top N, graph dates/gaps/zero baseline, weekly CSV/CSV.GZ/XLSX import/conflict/restart behavior, filtered weekly export, first-run seed preservation, invalid seed rejection, read-only analytics, and separate position/listener showings. Tiny fixture databases stayed on D:. The full suite and previously reported broad suites were not rerun.

The actual handover ZIP passed CRC verification. Its installer was extracted once into D: temporary storage; SHA-256 matched the ZIP's `SHA256SUMS.txt`. One installation completed successfully into an isolated D: destination, with no previous installation registration present.

One installed-app GUI session used a fresh D: profile, no Python on PATH and no source `PYTHONPATH`. All checks passed:

- Genuine daily, source-weekly and daily-derived dashboards, graphs and rankings.
- All seven navigation pages.
- Song graph actual chart dates, gap-aware rendering, hover connection and zero lower axis.
- Song stream showings, artist positions, album positions and separate listener snapshots, including repeat indicators and display-only Hide Repeats.
- Filtered genuine-data CSV and XLSX export/readback.
- One tiny synthetic weekly CSV imported into the isolated QA profile only; importing it twice left one observation.

A separate headless restart of the installed executable confirmed that this QA import survived, the existing database was not replaced by the seed, and `quick_check=ok`. The QA profile had 733,770 genuine song rows before its one test row; no synthetic row was added to the development database, release seed, Setup or ZIP. The isolated installation was successfully uninstalled and its large QA database removed. Actual receipts remain in `local-data/v018-work/qa-results/acceptance.json` and `persistence.json`.

## Build and delivery

Exactly one successful PyInstaller distribution, one Inno Setup installer and one handover ZIP were produced. All build/temp/cache paths were redirected to D:. No raw dataset, training CSV, temporary database, debug log or redundant standalone EXE is inside the ZIP.

| Artifact | Repository-relative path | Bytes |
|---|---|---:|
| Windows EXE | `local-data/v018-work/release/dist/USMusicChartsAnalytics/USMusicChartsAnalytics.exe` | Included in the 3,069,989,726-byte standalone distribution |
| Immutable seed | `local-data/v018-work/release/dist/USMusicChartsAnalytics/_internal/seed/analytics.sqlite3` | 2,730,164,224 |
| Setup | `local-data/v018-work/release/USMusicChartsAnalytics-0.1.8-InternalSetup.exe` | 713,547,450 |
| Handover | `local-data/v018-work/release/USMusicChartsAnalytics-0.1.8-INTERNAL-READY.zip` | 713,573,871 |

ZIP SHA-256: `d5120f9830dccf3d668ace5e322e4354ce88e0f37d4aceac1bbd6a35eeae6861`.

Setup SHA-256: `7710d58d3f6dc4a7ff402a14d8adfe99b4298f1b7309c96b870b020f715bd3de`.

Seed SHA-256: `47cb1c3f1f63ba4d0627738b6e92281d8bb5974e2df940f4abcd3957fff05221`.

The source database was checkpointed, then temporarily hard-linked for collection without another full staging copy. The collected independent seed's hash matched, the staging link was removed, and the collected seed was marked read-only. First launch initializes a writable database only when none exists; existing imports are preserved. Installed operation does not access Downloads or the development database.

Dependency-r3 notices, Qt sources/replacement materials and runtime prerequisite terms are retained inside Setup/the standalone distribution. A mechanical audit of 150 native files found no bundled Microsoft runtime DLLs or unresolved regular imports on this host. Three NumPy/Pandas build copies had private MSVCP import names normalized to the official system DLL name; hashes and recipe are retained. Installed Python packages were not modified. Setup checks the official Visual C++ v14 x64 prerequisite instead of bundling/downloading it.

## Storage and remaining limitations

- Before work: C: 1,164,906,496 bytes free; D: 35,457,855,488 bytes free.
- After large-task cleanup snapshot: C: 19,639,685,120 bytes free; D: 15,815,553,024 bytes free. Drive-wide changes also reflect activity outside this task; no existing user files were moved or deleted to clear C:.
- Peak observed temp/cache/PyInstaller storage: 6,932,793,646 bytes (6.46 GiB), plus about 0.18 GiB of tool/material staging. Approximate task temporary peak: 6.64 GiB. Monitored D: free space stayed above 8,950,681,600 bytes.
- Task temporary storage recovered: 6,858,806,733 bytes (6.39 GiB), including QA uninstall and individual removal of its large database and extracted installers.
- Recursive directory cleanup was tool-blocked. About 269,210,055 bytes (0.25 GiB) of small fixtures, caches, compiler tools and extracted material staging remain under `local-data/v018-work/{temp,cache,build,tools,reused-materials}`. They are not part of the release ZIP. No redundant large QA database remains.
- External dataset redistribution authorization and independent source authenticity remain unestablished. Weekly song coverage is sampled; exact track-to-album membership remains unavailable. No data was fabricated to match the old seed's counts. No clean-Windows VM, signed release or external-delivery approval is claimed.
