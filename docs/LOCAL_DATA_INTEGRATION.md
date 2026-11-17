# Local development integration

## Current integration: 2026-11-17

The existing isolated database was extended in place, without replacing the per-user database or repeating completed metadata/album/listener/artist imports. Current coverage is **721,171 US daily song observations** on **3,606 dates**, 2017-01-01 through 2026-11-15, for **15,152 stable track IDs** and **316,705,690,324 chart streams**. Every calendar date in that interval has some observations; this is not a completeness/authenticity certification. Invalid source rows and short chart dates remain unfilled.

`D:\Downloads\charts_songs_daily.csv` (11,128,590,058 bytes) was streamed once: 45,262,030 rows scanned, 44,540,833 non-US rows excluded, 26 invalid US rows rejected, and 721,171 observations accepted. Exact supplied artist URI relationships added 3,234 links. Source names are retained whole; no name-based person or album inference occurs.

`D:\Downloads\charts.csv\charts.csv` (3,483,476,388 bytes) was streamed once: 26,173,514 rows scanned, 19,957,720 non-US Top 200 rows and 5,851,610 other-chart rows excluded. It supplies 210,976 identical stable-ID overlaps, 152,507 same-ID conflicts, and 701 different-ID conflicts occupying an established date/rank slot. No additional observations from this file remain in totals. The 701 rows initially classified as new identities were quarantined after slot-level verification, with exact incoming values retained rather than merging IDs or double-counting the same chart slot. Only this task's incoming batch was corrected; earlier source observations are unchanged. Conflict totals are **153,208**. Of same-ID conflicts, 51 differ in streams, 573 in position, and 152,174 in labels; these categories overlap. `integration_conflicts` and `integration_slot_conflicts` retain the differences for review.

`D:\Downloads\charts_artists_daily.csv` (3,082,532,361 bytes) was already complete and was skipped using its manifest. Its 368,000 US daily positions cover 866 artists and 1,840 dates, 2021-10-21 through 2026-11-15. The source does not supply direct artist streams. Existing 61,588 album positions and 3,262,204 listener snapshots remain separate and unchanged. The app exposes all three metrics through **Chart showings > Source**, without inventing song/album membership or stream totals.

Source-weekly songs remain **12,599 observations**, 2,711 tracks, 63 dates, 2022-01-06 through 2026-10-08, totaling **42,913,401,825 streams**. These are sampled weeks, not continuous weekly history. Monday-Sunday derived weeks use only observed daily records, with 131,729 track/week observations on 516 Sunday reporting dates; derived and source-weekly streams never combine. The historical v0.1.7 figures (716,997 daily, 65,599 source-weekly, 125,361 derived track/weeks) are comparison figures, not targets used to manufacture rows.

Current entities/relationships: 220,884 tracks, 75,200 artists, 26,631 albums, 349,341 track-to-artist links, 28,984 album-to-artist links, **0 track-to-album links**, and 705,473 retained URL references. Source-only alternate IDs can remain in metadata without an accepted chart observation. The database occupies 2,730,164,224 bytes; free pages from the tiny quarantine were not reclaimed through a redundant full-database rebuild.

All generated databases, staging, caches, test profiles, build work and release artifacts for this task use `local-data/v018-work` on D:. Files were checked for age and opened with Windows handles excluding active writers. Large daily sources commit 2,000-row batches with checkpoints and progress records; an interrupted file is never marked complete. File SHA-256 values, source paths, schema fingerprints for newly streamed sources, exclusions and conflicts are in `source-manifest.json`/SQLite. Unchanged files retain their previously calculated hashes without a full rescan. Temporary storage is monitored; no raw multi-GB CSV was copied.

The release seed is a frozen snapshot of this integration, initialized only when a user database does not already exist. External data redistribution authorization and original publisher/version remain unestablished: the handover is **INTERNAL-READY**, not FINAL-CLIENT. See [release coverage](V018_DATA_COVERAGE.md) and [installation instructions](V018_INSTALLATION_GUIDE.md).

## Earlier integration: 2026-11-16

The following is the retained earlier integration record; its then-current sizes, test totals and packaging status are historical, superseded by the current section above.

Integrated on 2026-11-16 and updated with album-chart and listener observations in one isolated database:
`local-data/v018-integration/database/analytics.db`.
The existing per-user database, downloads, and previous releases are unchanged.
Launch this data with `scripts/run_integrated.ps1`; normal installed application data is separate.

| Completed source | Category | Imported source rows |
|---|---|---:|
| `artists.csv` | Artist metadata | 74,291 |
| `albums.csv` | Album metadata | 26,631 |
| `songs.csv` | Track metadata | 218,095 |
| `artwork.csv` | Artwork URL snapshots; images not downloaded | 312,520 |
| `links.csv` | Spotify references and retained external-link metadata | 147,917 |
| `spotify_top200_positions_2022.csv.gz` | US source-weekly observations with streams | 2,600 |
| `spotify_top200_positions_2023.csv.gz` | US source-weekly observations with streams | 2,600 |
| `spotify_top200_positions_2024.csv.gz` | US source-weekly observations with streams | 2,600 |
| `spotify_top200_positions_2025.csv.gz` | US source-weekly observations with streams | 2,600 |
| `spotify_top200_positions_2026.csv.gz` | US source-weekly observations with streams | 2,199 |
| `charts_albums_weekly.csv` | US weekly album positions; stored separately, no stream counts supplied | 61,588 |
| `artist_listeners_daily.csv` | Artist listener snapshots; stored separately from chart streams | 3,262,204 |

Both new files are owner-supplied; their original publisher/version is not independently established. The album file has 3,040,175 rows across 51 markets, including 61,588 US rows on 308 Thursday reporting dates from 2020-10-22 to 2026-11-12. Its US positions range from 1 to 200 and its 22-character Spotify album IDs are usable. This is structurally consistent with weekly US album chart positions, but the supplied export's authenticity is not independently verified. The file has no `streams` column, so the positions are not converted to stream totals. Of 2,099 distinct US album IDs, 1,896 match existing album metadata. No track-to-album relationships are inferred.

The listener file has 3,262,204 valid rows for 28,135 Spotify artist IDs and 130 observed dates from 2026-06-08 to 2026-11-16; it is not a continuous daily series. All rows are stored as listener metrics, never as chart streams. Of the distinct artist IDs, 26,529 match existing artist metadata; other valid IDs remain identifiable by their supplied IDs. Other personal files and partial downloads are not opened. Exact paths, byte sizes, timestamps, checksums, import counts, coverage, exclusions, and conflicts are recorded in `local-data/v018-integration/source-manifest.json` and SQLite `integration_files`.

Album positions and listener metrics have separate tables and query methods; neither changes song chart observations. The database still has **12,599 US song-weekly observations**, **2,711 charting tracks**, and **63 reporting dates**, from **2022-01-06 to 2026-10-08**. These are sampled/partial weeks, not continuous historical coverage. The song source-weekly stream sum remains **42,913,401,825**. Daily and daily-derived weekly streams remain absent rather than being fabricated.

Stable-ID relationships total **346,107 track-to-artist links** and **28,984 album-to-artist links**. There are **705,473 retained URL references**. Source credits remain intact; artist names are not split to infer identities. Additional source metadata, including labels, release dates, external-link details, and track URI lists, is retained in `entity_metadata` without merging distinct track IDs.

No supplied file establishes track-to-album membership. **Track-to-album links remain empty**; weekly album positions are independently queryable by album ID, date, and rank and are not the stream-based album rankings derived from linked charting tracks. Album names are never used to guess membership. Detail dialogs show bounded, selectable Spotify/artwork URL references without fetching or claiming verified artwork.

The two new sources added **0 duplicate observations, 0 conflicts, and 0 invalid rows**; **2,978,587 non-US album-chart rows** were excluded. The initial integration's two invalid rows remain documented: `albums.csv` row 3904 has an empty album name; the 2026 weekly file row 68823 lacks a required track/artist label. Repeated observations and metadata relationships are protected by stable keys; conflicting existing records are preserved and reported.

The v0.1.7 ZIP was listed without extraction: it contains an installer, not a standalone SQLite seed. No standalone recovered seed was found in the bounded known locations checked, so no seed migration or executable extraction was attempted.

The persistent database now occupies **1,738,084,352 bytes (about 1.62 GiB)**, up from 766,246,912 bytes. Transactions run per source file, with 2,000-row batches, bounded temporary tables, writer-excluding source handles on Windows, free-space checks, and WAL checkpoints between files. Temporary growth is checked against 3 GiB; no full-database backup copies are made. Source files newer than 60 seconds or held by a writer are skipped. An unchanged completed file is skipped using its recorded size/timestamp and previously calculated SHA-256, without rescanning it.

To add later completed files, run from the repository after setting up the source environment:

```powershell
$env:PYTHONPATH = 'src'
python -m spotify_historical_analytics.local_integration --downloads 'D:\Downloads' --data-dir 'local-data\v018-integration'
```

The workflow recognizes the five metadata schemas, song-weekly exports' `cc,week_end,rank,streams,track_id,title,artists,artist_uris` fields, album-weekly position rows, and artist listener snapshots. Song-week end is explicit and must be Thursday; its start is six days earlier. Album positions and listener snapshots use their own tables and queries. Invalid IDs, positions, counts, or dates do not become observations. A destination containing an existing user database is refused. Other supported daily/weekly formats can use the existing application importers against this isolated database.

Verification: 18 focused integration checks passed; the integrated database returned `quick_check=ok`, with 0 duplicate album-chart identities and unchanged song-weekly counts/date coverage. Unchanged-source skipping was confirmed for both new sources. No installer, executable, screenshots, or ZIP were produced; packaging and complete historical coverage remain pending.
