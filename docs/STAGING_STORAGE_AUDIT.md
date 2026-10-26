# Research Staging Storage Audit

**Run date:** 2026-10-26  
**Boundary:** External research SQLite only. The production app database, source CSV, Zenodo ZIP, and Windows executable were not modified.

## Before and after

| Item | Original staging | Compact staging |
|---|---:|---:|
| Path | `D:\Study Material\University\Spotify-Dataset-Research\staging\research_staging.sqlite` | `D:\Study Material\University\Spotify-Dataset-Research\staging\research_staging_compact.sqlite` |
| File size | 13,912,154,112 bytes | 325,226,496 bytes |
| Source rows reconciled | 26,173,514 | 26,173,514 |
| Accepted observations | 455,031 | 455,031 |
| Rejected observations | 25,718,483 row-level JSON records retained in original | 25,718,483 aggregate counts |
| Diagnostic raw rejection samples | Millions in legacy row-level table | 46 bounded samples |
| SQLite integrity check | Existing database left untouched | `ok` |

The compact database is about 97.7% smaller by file size. Its input file checksum is `8238a106f723af9b1d3b857b78ec43f7147d82472b491c63853bcbcc3c23cb1b`. Counts were reconciled against the original `staged_files` manifest and accepted-row count; the sum of compact rejection aggregates also equals the source rejected-row count.

The original database was opened read-only by the compaction routine. No automatic replacement, deletion, `VACUUM`, or in-place rewrite was performed. Both files remain outside the repository and production app data.

## Why the old database was large

The legacy schema stored one full raw-JSON row per rejected observation: 25,718,483 rejection rows. The measured rejection classification was:

- `non_us_or_unknown_region`: 25,718,457 rows.
- `position_out_of_range:50`: 26 rows, all identified from the bounded sample as `viral50` rank 51.

Rejected-region details are aggregated without storing every rejected row. For example, 451,793 rows carried the source region label `Global`. The compact database retains a bounded diagnostic sample (20 examples per ordinary reason, up to 100 for out-of-range-rank reasons); all 26 rank anomalies are retained. The old row-level table remains available in the preserved original database.

## Compact build safeguards

`scripts\compact_research_staging.py` creates a new `.building` sibling database and refuses to overwrite either an existing final database or existing build file. It:

1. Opens the original database read-only and requires a completed source row matching dataset ID, version, and file checksum.
2. Hashes the source before and after processing.
3. Estimates required free space as accepted raw JSON bytes plus 2,048 bytes per accepted row plus 512 MiB, or a larger operator-supplied minimum.
4. Processes the source in bounded batches and reports row progress.
5. Aggregates rejection counts by reason and bounded details; raw rejected rows are not inserted in the compact legacy rejection table.
6. Reconciles source-seen/accepted/rejected counts against compact observations and aggregate rejection totals.
7. Checks `PRAGMA integrity_check` and only then renames the completed build to a new output path.

The build preflight measured 32,154,443,776 bytes free and required 1,580,719,694 bytes under that estimate. The result was a 325,226,496-byte compact database with `integrity_check=ok`. A failed or mismatched build is not promoted; any `.building` file is preserved for inspection rather than automatically deleted.

The research staging schema is now version 4, and the parser normalization version is 3. A completed file processed with an older normalization version returns `reprocess_required`; old accepted/rejected rows are not silently deleted. Reprocessing requires explicit `force_reprocess=True`, while compaction always targets a new database.

## Source schema and report outputs

The compact staging schema contains:

- `staged_files`: source version, source SHA-256, row totals, status, timestamps, and parser version.
- `staged_observations`: canonical accepted rows plus source-row provenance and raw JSON.
- `staged_rejection_counts`: reason/detail aggregate counts.
- `staged_rejection_samples`: bounded raw diagnostic examples.
- `source_rights`: source/version rights state, copied without granting new approval.

Machine-readable quality reports are in the external `reports\phase6b_compact_audit\` directory. They include year/month/date coverage, candidate calendar gaps, stream availability, zero-stream counts, incomplete Top 200/Viral 50 dates, duplicate/conflicting identity checks, rejection detail counts, and invalid-rank samples.

## Reproduction

Use a new target database and report directory for a fresh build; the script refuses to overwrite existing outputs.

```powershell
python scripts\compact_research_staging.py `
  --source-db "D:\Study Material\University\Spotify-Dataset-Research\staging\research_staging.sqlite" `
  --source-file "D:\Study Material\University\Spotify-Dataset-Research\02_Dhruvil_Spotify_Charts\datasets\dhruvildave\spotify-charts\versions\85\charts.csv" `
  --target-db "D:\Study Material\University\Spotify-Dataset-Research\staging\research_staging_compact_NEW.sqlite" `
  --dataset "dhruvildave/spotify-charts@85" `
  --report-dir "D:\Study Material\University\Spotify-Dataset-Research\reports\phase6b_compact_audit_NEW"
```

`--refresh-existing` is narrowly intended to supplement rank-diagnostic samples and refresh quality reports for a compact database that already has a build manifest. It does not reprocess or replace source observations.

The compact research database is not a production database and must not be copied into the Windows application's data directory or executable.
