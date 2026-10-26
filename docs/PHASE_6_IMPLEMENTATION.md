# Phase 6: Dataset Research Pipeline

## Scope and safety boundary

Phase 6 adds an optional research-only workflow around two pinned Kaggle dataset versions. It does not make KaggleHub a runtime dependency of the desktop app, does not add chart data to the packaged executable, and does not silently import records into the existing production database. Research files and the separate SQLite staging database belong outside the project and app-data roots.

Kaggle listings were checked on 2026-10-26:

| Dataset | Pinned listing version | Listing metadata | Permission status |
|---|---:|---|---|
| `gonzalopezgil/spotify-charts-daily-updated` | 146 | CC BY-SA 4.0; listing describes daily songs/artists, weekly albums, entity tables and additional listener/artwork/link files | UNVERIFIED |
| `dhruvildave/spotify-charts` | 85 | ODbL 1.0 database / original-author contents; listing advertises global Top 200 and Viral 50 history beginning 2017 | UNVERIFIED |

The listings do not prove upstream Spotify rights, accurate USA coverage, commercial-use permission, derived-metric permission, or redistribution permission. The first listing reported a zero-byte distribution size in its page metadata; that is not a usable size estimate. The second listing reported a 991,225,045-byte archive. These are page snapshots, not local-file measurements.

## Implemented

- `scripts/download_historical_datasets.py` uses the documented KaggleHub `dataset_download` function with explicit pinned versions, separate cache roots, no force download, an exclusive local lock, reuse checks, and partial-download detection.
- KaggleHub is installed only through the optional `research` extra. The Windows executable's normal app startup does not import it or require Kaggle credentials.
- The research SQLite database has independent `staged_files`, `staged_observations`, `staged_rejections`, and version-specific `source_rights` tables. It is not the application database.
- The current staging schema is version 4 and normalization is version 3. Rejections are aggregated by reason and safe detail values, with bounded diagnostic samples. Existing row-level rejection tables are preserved; completed files with older normalization versions are not silently deleted or reprocessed.
- `scripts/compact_research_staging.py` rebuilds into a separate sibling database after a free-space preflight, source-checksum check, row reconciliation, and SQLite integrity check. It does not replace the original database.
- `scripts/audit_mgdplus_archive.py` CRC-checks, inventories, and audits MGD+ members directly from the ZIP without extraction or production import.
- The latest Kaggle preflight uses an unversioned KaggleHub dataset handle only when an exact-version cache is absent and conservative disk headroom is sufficient. A failed preflight never calls KaggleHub.
- CSV/CSV.GZ, Parquet, XLSX/XLSM and JSONL are read in bounded batches. Raw rows are retained in staging; source files are left untouched. Archives are CRC-checked and inventoried without a second full extracted copy.
- Coverage and overlap summaries are computed with SQLite aggregates and streamed to CSV; the report step does not materialize all staged observations in Python memory.
- Per-file audit rows record measured processing seconds and sampled process peak RSS when the chart schema is supported. These figures are local measurements, not performance guarantees.
- USA normalization accepts only `US`, `USA`, `United States`, and `United States of America`. Global, other, and unknown markets are rejected with row-level reasons.
- Stable track IDs are taken directly from supplied ID fields or extracted only from an exact HTTPS `open.spotify.com/track/<22-character-ID>` URL; name similarity and unrelated URLs are not used as identity evidence.
- Streams, popularity, monthly listeners, chart positions, and album counts are kept distinct. Missing streams remain NULL; numeric zero remains zero.
- Daily and weekly cadence and song/artist/album categories stay separate. No observations from weekly albums or artist metrics enter song-stream rankings.
- Weekly song rows can be transferred only when explicit week start and end dates are supplied; the current application schema is not populated with guessed weekly intervals.
- Exact-ID overlap comparison reports matching duplicates separately from conflicting values. It neither sums, deletes, nor silently chooses a source. Name-only matches are not treated as verified duplicates.
- An explicit source/version approval record with a cited evidence file is required before the controlled song-only production-import function can run. The evidence is an operator-supplied reference; the code does not make legal approval decisions.
- Machine reports include dataset inventory, coverage by year/month, candidate missing dates, conflicts, overlap, import-validation counts, and a written coverage summary. Empty years are explicitly reported as having no validated observations.

## Current run outcome

The requested `D:\Spotify-Dataset-Research` root could not be created because the current user has read/execute-only access on `D:\`. This is an access-control limitation; the workflow did not attempt to change ACLs or elevate privileges. The download attempt was therefore directed to the writable sibling `D:\Study Material\University\Spotify-Dataset-Research`.

The pinned v146 request for the first dataset returned HTTP 404. The pinned v85 dataset downloaded as a 3,483,476,388-byte `charts.csv` containing 26,173,514 rows. Of those, 455,031 US candidate rows were staged and 25,718,483 rejected (25,718,457 non-US/unknown region; 26 out-of-range ranks). The accepted rows span 2017-01-01 through 2021-12-31, have 14,649 distinct track IDs derived from exact Spotify track URLs, and have no separate artist IDs or album mappings. No observations were staged for 2022–2026. There are 12 calendar-step gap candidates; the expected chart schedule is not verified.

The schema-v3 per-file audit elapsed time was 600.18 seconds, including hashing, row processing, staging, and inventory. Sampled peak process RSS during row processing was 139,591,680 bytes (about 133.1 MiB). These are measurements for the exact local file and environment, not performance guarantees. No rights were approved and no production imports were performed. The per-file checksum, actual schema, detailed coverage, rejections, and permission state are in that root's `reports\dataset_download_status.json`, `reports\dataset_inventory.csv`, `reports\coverage_by_year.csv`, `reports\coverage_by_month.csv`, `reports\missing_dates.csv`, `reports\source_overlap.csv`, `reports\data_conflicts.csv`, and `reports\import_validation.json`.

The research staging SQLite file measured 13,912,154,112 bytes after storing accepted and rejected source rows. D: had 32,276,529,152 bytes free at that measurement. Research storage is intentionally outside the application database and repository.

## Phase 6B findings (2026-10-26)

The original v85 `charts.csv` was reprocessed into `staging\research_staging_compact.sqlite` under the external research root. The source file SHA-256 remained `8238a106f723af9b1d3b857b78ec43f7147d82472b491c63853bcbcc3c23cb1b`; the compact file reconciled 26,173,514 seen rows to 455,031 accepted and 25,718,483 rejected, and `PRAGMA integrity_check` returned `ok`. The original staging file was not replaced or deleted. Its measured size was 13,912,154,112 bytes; the compact staging file measured 325,226,496 bytes.

The 26 `position_out_of_range:50` rows were inspected: all 26 are `viral50` records at rank 51. They remain rejected; they were not reclassified as Top 200 observations. Other rejections are non-US or unknown-region rows, including 451,793 rows marked `Global`. Top 200 observations in v85 have stream values; Viral 50 rows do not.

The current Kaggle listing metadata reported version 146 and 14,962,095,987 bytes for `gonzalopezgil/spotify-charts-daily-updated`. No matching local cache was found. Available disk space at preflight was 31,576,604,672 bytes; the guard required 47,033,771,609 bytes (3x the listing size plus a 2 GiB reserve). The status was `SKIPPED_INSUFFICIENT_SPACE`; the unversioned KaggleHub request was **not called**, and no download was attempted.

Zenodo record 8086643's 364,603,433-byte `MGDplus.zip` was downloaded to the external research root. Its MD5 matched the record metadata, CRC testing passed, SHA-256 was `93ad6b8dd7e8443fbfbece0d56bf74120073f69b1315706e305b995301e5392a`, and no extraction was performed. Its US regional chart member has Top 200 rows from 2017-01-01 through 2022-03-13, but no Viral chart member. A key-based comparison against v85 found 363,785 shared date/track-ID/rank keys with identical stream values and no stream conflicts; the sources are not thereby established as independent or authoritative.

Machine-readable outputs are outside the repository under `D:\Study Material\University\Spotify-Dataset-Research\reports\phase6b_compact_audit\`, `reports\phase6b_zenodo_audited\`, and `reports\kaggle_latest_download_preflight.json`. The detail and remaining year gaps are documented in [PHASE_6B_RESULTS.md](./PHASE_6B_RESULTS.md), [STAGING_STORAGE_AUDIT.md](./STAGING_STORAGE_AUDIT.md), and [MISSING_YEARS_PLAN.md](./MISSING_YEARS_PLAN.md).

## Known limitations

- This is a research audit pipeline, not a client-facing Data Management UI.
- JSON arrays and arbitrary SQLite tables are inventoried but not normalized; JSONL is batch-readable. ZIP archives are CRC-checked and inventoried; the MGD+ audit reads the selected US chart member in place, but does not import archive contents into staging.
- Only confirmed field aliases are normalized. Unsupported schemas remain inventory-only or produce explicit validation rejections; no guesses are made from similarly named fields.
- No source precedence policy is inferred. Conflicts remain unresolved until an owner supplies evidence and a documented decision.
- Artist and album data remain isolated from song-stream calculations. A future metadata/entity importer must validate exact IDs and metric meaning before wiring those categories into production.
- Calendar gaps are candidates, not proof of missing expected charts. No year is called complete without a verified reporting calendar.
- A Kaggle dataset license does not settle Spotify Content/database rights or the intended commercial product use. Obtain current platform/legal review before production use.

## Reproducible commands

```powershell
python -m pip install -e ".[research,test]"
python scripts/download_historical_datasets.py --download --research-root "D:\Spotify-Dataset-Research"
python scripts/download_historical_datasets.py --audit-only --research-root "D:\Spotify-Dataset-Research"
python -m pytest -q
python -m compileall -q src scripts tests
git diff --check
```

If the default research root is not writable, pass a separate writable research directory. Do not place research files in the app's Local AppData database folder. If Kaggle requires authentication, authenticate locally with KaggleHub's documented `kagglehub.login()` flow or a secure credential file/environment variable; never paste a token into source, logs, or chat.
